#!/usr/bin/env python3
"""Generate valid Apple Shortcuts binary plist (.shortcut) files for ClipSave."""

from __future__ import annotations

import plistlib
import uuid
import zipfile
from pathlib import Path
from typing import Any

OBJ_REPLACEMENT = "\ufffc"


def new_uuid() -> str:
    return str(uuid.uuid4()).upper()


def token_attachment(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "Value": value,
        "WFSerializationType": "WFTextTokenAttachment",
    }


def var_attachment(name: str) -> dict[str, Any]:
    return token_attachment({"Type": "Variable", "VariableName": name})


def action_output_attachment(output_uuid: str, output_name: str) -> dict[str, Any]:
    return token_attachment(
        {
            "OutputName": output_name,
            "OutputUUID": output_uuid,
            "Type": "ActionOutput",
        }
    )


def text_token_string(parts: list[str | dict[str, Any]]) -> dict[str, Any]:
    """Build a WFTextTokenString from literal strings and attachment dicts."""
    text_buf: list[str] = []
    attachments: dict[str, dict[str, Any]] = {}
    pos = 0
    for part in parts:
        if isinstance(part, str):
            text_buf.append(part)
            pos += len(part)
        else:
            text_buf.append(OBJ_REPLACEMENT)
            attachments[f"{{{pos}, 1}}"] = part
            pos += 1
    return {
        "Value": {
            "attachmentsByRange": attachments,
            "string": "".join(text_buf),
        },
        "WFSerializationType": "WFTextTokenString",
    }


def dict_field_items(entries: list[tuple[str, Any, int]]) -> dict[str, Any]:
    """Build WFDictionaryFieldValue items.

    item_type: 0 = Text, 3 = Number, 4 = Boolean
    """
    items = []
    for key, val, item_type in entries:
        if item_type == 4:
            wf_value = {"Value": bool(val), "WFSerializationType": "WFBooleanSubstitutableState"}
        elif isinstance(val, dict) and "WFSerializationType" in val:
            wf_value = val
        else:
            wf_value = text_token_string([str(val)])
        items.append(
            {
                "WFItemType": item_type,
                "WFKey": text_token_string([key]),
                "WFValue": wf_value,
            }
        )
    return {
        "Value": {"WFDictionaryFieldValueItems": items},
        "WFSerializationType": "WFDictionaryFieldValue",
    }


def build_clipsave_shortcut(
    include_quality_menu: bool = True,
    default_server_url: str = "https://your-clipsave-server.example.com",
    default_api_key: str = "change-me-to-a-strong-secret-key",
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []

    # 0. Server URL (Import Question 0)
    server_url_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
            "WFWorkflowActionParameters": {
                "UUID": server_url_uuid,
                "WFTextActionText": default_server_url,
            },
        }
    )
    # 1. Set Variable ServerURL
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
            "WFWorkflowActionParameters": {
                "WFInput": action_output_attachment(server_url_uuid, "Text"),
                "WFVariableName": "ServerURL",
            },
        }
    )

    # 2. API Key (Import Question 1)
    api_key_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
            "WFWorkflowActionParameters": {
                "UUID": api_key_uuid,
                "WFTextActionText": default_api_key,
            },
        }
    )
    # 3. Set Variable APIKey
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
            "WFWorkflowActionParameters": {
                "WFInput": action_output_attachment(api_key_uuid, "Text"),
                "WFVariableName": "APIKey",
            },
        }
    )

    # 4. Check if Shortcut Input exists, else read Clipboard
    if_input_gid = new_uuid()
    if_input_out_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_input_gid,
                "WFCondition": 100,  # Has any value
                "WFControlFlowMode": 0,
                "WFInput": {
                    "Type": "Variable",
                    "Variable": token_attachment({"Type": "ExtensionInput"}),
                },
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
            "WFWorkflowActionParameters": {
                "UUID": new_uuid(),
                "WFTextActionText": text_token_string([{"Type": "ExtensionInput"}]),
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_input_gid,
                "WFControlFlowMode": 1,
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.getclipboard",
            "WFWorkflowActionParameters": {"UUID": new_uuid()},
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_input_gid,
                "UUID": if_input_out_uuid,
                "WFControlFlowMode": 2,
            },
        }
    )

    # Detect URL from Share text / Clipboard
    detect_url_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.detect.link",
            "WFWorkflowActionParameters": {
                "UUID": detect_url_uuid,
                "WFInput": action_output_attachment(if_input_out_uuid, "If Result"),
            },
        }
    )

    first_url_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.getitemfromlist",
            "WFWorkflowActionParameters": {
                "UUID": first_url_uuid,
                "WFInput": action_output_attachment(detect_url_uuid, "URLs"),
                "WFItemSpecifier": "First Item",
            },
        }
    )

    # If no URL detected, ask user to paste URL
    if_url_gid = new_uuid()
    if_url_out_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_url_gid,
                "WFCondition": 100,
                "WFControlFlowMode": 0,
                "WFInput": {
                    "Type": "Variable",
                    "Variable": action_output_attachment(first_url_uuid, "Item from List"),
                },
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
            "WFWorkflowActionParameters": {
                "UUID": new_uuid(),
                "WFTextActionText": text_token_string(
                    [
                        {
                            "OutputName": "Item from List",
                            "OutputUUID": first_url_uuid,
                            "Type": "ActionOutput",
                        }
                    ]
                ),
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_url_gid,
                "WFControlFlowMode": 1,
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.ask",
            "WFWorkflowActionParameters": {
                "UUID": new_uuid(),
                "WFAskActionPrompt": "Dán link video cần tải (TikTok, Douyin, IG, YouTube, X...)",
                "WFInputType": "URL",
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_url_gid,
                "UUID": if_url_out_uuid,
                "WFControlFlowMode": 2,
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
            "WFWorkflowActionParameters": {
                "WFInput": action_output_attachment(if_url_out_uuid, "If Result"),
                "WFVariableName": "TargetURL",
            },
        }
    )

    # Mode & Quality selection
    if include_quality_menu:
        menu_gid = new_uuid()
        opt_hd = "Video chất lượng cao (Không watermark)"
        opt_720 = "Video tiết kiệm dung lượng (720p)"
        opt_audio = "Chỉ tải âm thanh (M4A)"

        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.choosefrommenu",
                "WFWorkflowActionParameters": {
                    "GroupingIdentifier": menu_gid,
                    "WFControlFlowMode": 0,
                    "WFMenuItems": [opt_hd, opt_720, opt_audio],
                    "WFMenuPrompt": "ClipSave — Chọn định dạng tải",
                },
            }
        )
        # Case 1: HD
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.choosefrommenu",
                "WFWorkflowActionParameters": {
                    "GroupingIdentifier": menu_gid,
                    "WFControlFlowMode": 1,
                    "WFMenuItemTitle": opt_hd,
                },
            }
        )
        m1_mode_uuid = new_uuid()
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": m1_mode_uuid, "WFTextActionText": "auto"},
            }
        )
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "WFInput": action_output_attachment(m1_mode_uuid, "Text"),
                    "WFVariableName": "SelectedMode",
                },
            }
        )
        m1_q_uuid = new_uuid()
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": m1_q_uuid, "WFTextActionText": "best"},
            }
        )
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "WFInput": action_output_attachment(m1_q_uuid, "Text"),
                    "WFVariableName": "SelectedQuality",
                },
            }
        )

        # Case 2: 720p
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.choosefrommenu",
                "WFWorkflowActionParameters": {
                    "GroupingIdentifier": menu_gid,
                    "WFControlFlowMode": 1,
                    "WFMenuItemTitle": opt_720,
                },
            }
        )
        m2_mode_uuid = new_uuid()
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": m2_mode_uuid, "WFTextActionText": "video"},
            }
        )
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "WFInput": action_output_attachment(m2_mode_uuid, "Text"),
                    "WFVariableName": "SelectedMode",
                },
            }
        )
        m2_q_uuid = new_uuid()
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": m2_q_uuid, "WFTextActionText": "720p"},
            }
        )
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "WFInput": action_output_attachment(m2_q_uuid, "Text"),
                    "WFVariableName": "SelectedQuality",
                },
            }
        )

        # Case 3: Audio
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.choosefrommenu",
                "WFWorkflowActionParameters": {
                    "GroupingIdentifier": menu_gid,
                    "WFControlFlowMode": 1,
                    "WFMenuItemTitle": opt_audio,
                },
            }
        )
        m3_mode_uuid = new_uuid()
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": m3_mode_uuid, "WFTextActionText": "audio"},
            }
        )
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "WFInput": action_output_attachment(m3_mode_uuid, "Text"),
                    "WFVariableName": "SelectedMode",
                },
            }
        )
        m3_q_uuid = new_uuid()
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": m3_q_uuid, "WFTextActionText": "best"},
            }
        )
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "WFInput": action_output_attachment(m3_q_uuid, "Text"),
                    "WFVariableName": "SelectedQuality",
                },
            }
        )
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.choosefrommenu",
                "WFWorkflowActionParameters": {
                    "GroupingIdentifier": menu_gid,
                    "UUID": new_uuid(),
                    "WFControlFlowMode": 2,
                },
            }
        )
    else:
        one_mode_uuid = new_uuid()
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": one_mode_uuid, "WFTextActionText": "auto"},
            }
        )
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "WFInput": action_output_attachment(one_mode_uuid, "Text"),
                    "WFVariableName": "SelectedMode",
                },
            }
        )
        one_q_uuid = new_uuid()
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": one_q_uuid, "WFTextActionText": "best"},
            }
        )
        actions.append(
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "WFInput": action_output_attachment(one_q_uuid, "Text"),
                    "WFVariableName": "SelectedQuality",
                },
            }
        )

    # POST /api/v1/resolve
    api_resp_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
            "WFWorkflowActionParameters": {
                "UUID": api_resp_uuid,
                "WFURL": text_token_string(
                    [
                        {"Type": "Variable", "VariableName": "ServerURL"},
                        "/api/v1/resolve",
                    ]
                ),
                "WFHTTPMethod": "POST",
                "WFHTTPHeaders": dict_field_items(
                    [
                        (
                            "X-API-Key",
                            text_token_string([{"Type": "Variable", "VariableName": "APIKey"}]),
                            0,
                        )
                    ]
                ),
                "WFHTTPBodyType": "Json",
                "WFJSONValues": dict_field_items(
                    [
                        (
                            "url",
                            text_token_string([{"Type": "Variable", "VariableName": "TargetURL"}]),
                            0,
                        ),
                        (
                            "mode",
                            text_token_string(
                                [{"Type": "Variable", "VariableName": "SelectedMode"}]
                            ),
                            0,
                        ),
                        (
                            "quality",
                            text_token_string(
                                [{"Type": "Variable", "VariableName": "SelectedQuality"}]
                            ),
                            0,
                        ),
                        ("audio_format", "m4a", 0),
                        ("ios_compatible", True, 4),
                    ]
                ),
            },
        }
    )

    # Read response.status
    status_val_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
            "WFWorkflowActionParameters": {
                "UUID": status_val_uuid,
                "WFDictionaryKey": "status",
                "WFInput": action_output_attachment(api_resp_uuid, "Contents of URL"),
            },
        }
    )

    # If status == "ok"
    if_ok_gid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_ok_gid,
                "WFCondition": 4,  # Equals
                "WFConditionalActionString": "ok",
                "WFControlFlowMode": 0,
                "WFInput": {
                    "Type": "Variable",
                    "Variable": action_output_attachment(status_val_uuid, "Dictionary Value"),
                },
            },
        }
    )

    items_val_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
            "WFWorkflowActionParameters": {
                "UUID": items_val_uuid,
                "WFDictionaryKey": "items",
                "WFInput": action_output_attachment(api_resp_uuid, "Contents of URL"),
            },
        }
    )

    # Repeat for each item in items
    repeat_gid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.repeat.each",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": repeat_gid,
                "WFControlFlowMode": 0,
                "WFInput": action_output_attachment(items_val_uuid, "Dictionary Value"),
            },
        }
    )

    item_dl_url_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
            "WFWorkflowActionParameters": {
                "UUID": item_dl_url_uuid,
                "WFDictionaryKey": "download_url",
                "WFInput": var_attachment("Repeat Item"),
            },
        }
    )

    downloaded_file_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
            "WFWorkflowActionParameters": {
                "UUID": downloaded_file_uuid,
                "WFURL": text_token_string(
                    [
                        {
                            "OutputName": "Dictionary Value",
                            "OutputUUID": item_dl_url_uuid,
                            "Type": "ActionOutput",
                        }
                    ]
                ),
            },
        }
    )

    item_type_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
            "WFWorkflowActionParameters": {
                "UUID": item_type_uuid,
                "WFDictionaryKey": "type",
                "WFInput": var_attachment("Repeat Item"),
            },
        }
    )

    if_audio_gid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_audio_gid,
                "WFCondition": 4,
                "WFConditionalActionString": "audio",
                "WFControlFlowMode": 0,
                "WFInput": {
                    "Type": "Variable",
                    "Variable": action_output_attachment(item_type_uuid, "Dictionary Value"),
                },
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.documentpicker.save",
            "WFWorkflowActionParameters": {
                "WFAskWhereToSave": True,
                "WFInput": action_output_attachment(downloaded_file_uuid, "Contents of URL"),
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_audio_gid,
                "WFControlFlowMode": 1,
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.savetocameraroll",
            "WFWorkflowActionParameters": {
                "WFInput": action_output_attachment(downloaded_file_uuid, "Contents of URL"),
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_audio_gid,
                "UUID": new_uuid(),
                "WFControlFlowMode": 2,
            },
        }
    )

    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.repeat.each",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": repeat_gid,
                "UUID": new_uuid(),
                "WFControlFlowMode": 2,
            },
        }
    )

    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.notification",
            "WFWorkflowActionParameters": {
                "WFNotificationActionBody": "Đã lưu media không watermark thành công!",
                "WFNotificationActionTitle": "ClipSave",
            },
        }
    )

    # Else (error)
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_ok_gid,
                "WFControlFlowMode": 1,
            },
        }
    )
    err_detail_uuid = new_uuid()
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
            "WFWorkflowActionParameters": {
                "UUID": err_detail_uuid,
                "WFDictionaryKey": "detail",
                "WFInput": action_output_attachment(api_resp_uuid, "Contents of URL"),
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.alert",
            "WFWorkflowActionParameters": {
                "WFAlertActionCancelButtonShown": False,
                "WFAlertActionMessage": text_token_string(
                    [
                        "Không thể tải video: ",
                        {
                            "OutputName": "Dictionary Value",
                            "OutputUUID": err_detail_uuid,
                            "Type": "ActionOutput",
                        },
                    ]
                ),
                "WFAlertActionTitle": "Lỗi ClipSave",
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": if_ok_gid,
                "UUID": new_uuid(),
                "WFControlFlowMode": 2,
            },
        }
    )

    import_questions = [
        {
            "ActionIndex": 0,
            "Category": "Parameter",
            "DefaultValue": default_server_url,
            "ParameterKey": "WFTextActionText",
            "Text": "Nhập URL Backend ClipSave của bạn (không có dấu / ở cuối):",
        },
        {
            "ActionIndex": 2,
            "Category": "Parameter",
            "DefaultValue": default_api_key,
            "ParameterKey": "WFTextActionText",
            "Text": "Nhập X-API-Key bảo mật (trùng với API_KEY trên server):",
        },
    ]

    return {
        "WFQuickActionSurfaces": [],
        "WFWorkflowActions": actions,
        "WFWorkflowClientVersion": "2302.0.4",
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowHasShortcutInputVariables": True,
        "WFWorkflowIcon": {
            "WFWorkflowIconGlyphNumber": 59771,
            "WFWorkflowIconStartColor": 4274264319,
        },
        "WFWorkflowImportQuestions": import_questions,
        "WFWorkflowInputContentItemClasses": [
            "WFURLContentItem",
            "WFSafariWebPageContentItem",
            "WFStringContentItem",
        ],
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowTypes": ["NCWidget", "ActionExtension", "Watch"],
    }


def main() -> None:
    dist_dir = Path(__file__).resolve().parents[1] / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    menu_plist = build_clipsave_shortcut(include_quality_menu=True)
    menu_out = dist_dir / "ClipSave.unsigned.shortcut"
    with menu_out.open("wb") as f:
        plistlib.dump(menu_plist, f, fmt=plistlib.FMT_BINARY)

    onetap_plist = build_clipsave_shortcut(include_quality_menu=False)
    onetap_out = dist_dir / "ClipSave-1Tap.unsigned.shortcut"
    with onetap_out.open("wb") as f:
        plistlib.dump(onetap_plist, f, fmt=plistlib.FMT_BINARY)

    shortcut_root = dist_dir.parent
    bundle_zip = dist_dir / "ClipSave-iOS-Bundle.zip"
    with zipfile.ZipFile(bundle_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(menu_out, arcname=menu_out.name)
        zf.write(onetap_out, arcname=onetap_out.name)
        for helper_name in ("sign_on_mac.sh", "GUIDE_IOS.md"):
            helper_path = shortcut_root / helper_name
            if helper_path.is_file():
                zf.write(helper_path, arcname=helper_name)

    print(f"Generated: {menu_out}")
    print(f"Generated: {onetap_out}")
    print(f"Packaged:  {bundle_zip}")


if __name__ == "__main__":
    main()
