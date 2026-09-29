import json
import glob
import re

EMOJI_ADD_CHANNEL_TAG = '<tg-emoji emoji-id="5771868281212245617">📢</tg-emoji>'
EMOJI_CHANNEL_TAG = '<tg-emoji emoji-id="5771695636411847302">📢</tg-emoji>'
EMOJI_BUNDLE_TAG = '<tg-emoji emoji-id="5877332341331857066">📁</tg-emoji>'
EMOJI_RENAME_BUNDLE_TAG = '<tg-emoji emoji-id="6021859047404214713">📁</tg-emoji>'
EMOJI_DELETE_TAG = '<tg-emoji emoji-id="5841541824803509441">🗑</tg-emoji>'
EMOJI_CLOSE_TAG = '<tg-emoji emoji-id="5807692706507399432">✖️</tg-emoji>'
EMOJI_EDIT_TAG = '<tg-emoji emoji-id="5879841310902324730">✏️</tg-emoji>'
EMOJI_STATISTIC_TAG = '<tg-emoji emoji-id="5931472654660800739">📊</tg-emoji>'

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as fp:
        d = json.load(fp)

    is_uzl = filepath.endswith('uzl.json')
    is_uzk = filepath.endswith('uzk.json')

    changed_count = 0
    for k, v in list(d.items()):
        if not isinstance(v, str):
            continue
        old_v = v
        new_v = v

        # 1. add_channel_msg
        if k == 'add_channel_msg':
            if is_uzl:
                new_v = re.sub(r'<b>📢\s*Kanal qo\'shish bo\'limi\s*:\s*</b>', f'<b>{EMOJI_ADD_CHANNEL_TAG} Yangi kanal qo\'shish bo\'limi :</b>', new_v)
            elif is_uzk:
                new_v = re.sub(r'<b>📢\s*Канал қошиш болими\s*:\s*</b>', f'<b>{EMOJI_ADD_CHANNEL_TAG} Янги канал қўшиш бўлими :</b>', new_v)
            else:
                new_v = re.sub(r'^<b>📢\s*', f'<b>{EMOJI_ADD_CHANNEL_TAG} ', new_v)

        # 2. need_channel_instruction_msg
        elif k == 'need_channel_instruction_msg':
            if is_uzl:
                new_v = re.sub(r'<b>📢\s*Kanal qo\'shish yo\'riqnomasi:\s*</b>', f'<b>{EMOJI_ADD_CHANNEL_TAG} Yangi kanal qo\'shish yo\'riqnomasi:</b>', new_v)
            elif is_uzk:
                new_v = re.sub(r'<b>📢\s*Канал қўшиш йўриқномаси:\s*</b>', f'<b>{EMOJI_ADD_CHANNEL_TAG} Янги канал қўшиш йўриқномаси:</b>', new_v)
            else:
                new_v = re.sub(r'<b>📢\s*', f'<b>{EMOJI_ADD_CHANNEL_TAG} ', new_v)

        # 3. settings_add_channel_title
        elif k == 'settings_add_channel_title':
            new_v = re.sub(r'^➕\s*<b>', f'{EMOJI_ADD_CHANNEL_TAG} <b>', new_v)

        # 4. Buttons (replace ➕ with 📢, no html tags in buttons!)
        elif k in ('add_channel_btn', 'add_new_channel_btn', 'add_channel_post_btn'):
            if is_uzl:
                new_v = "📢 Yangi kanal qo'shish"
            elif is_uzk:
                new_v = "📢 Янги канал қўшиш"
            else:
                new_v = re.sub(r'^➕\s*', '📢 ', new_v)

        # 5. bundles_title, no_bundles_msg, choose_bundle_to_add, choose_bundle_to_remove, bundle_share_card, bundle_shared_import_prompt
        elif k in ('bundles_title', 'no_bundles_msg', 'choose_bundle_to_add', 'choose_bundle_to_remove', 'bundle_share_card', 'bundle_shared_import_prompt'):
            new_v = re.sub(r'^📁\s*<b>', f'{EMOJI_BUNDLE_TAG} <b>', new_v)

        # 6. bundle_details
        elif k == 'bundle_details':
            new_v = re.sub(r'^📁\s*<b>', f'{EMOJI_BUNDLE_TAG} <b>', new_v)
            new_v = re.sub(r'📢\s*<b>', f'{EMOJI_CHANNEL_TAG} <b>', new_v)

        # 7. bundle_enter_name, bundle_enter_new_name
        elif k in ('bundle_enter_name', 'bundle_enter_new_name'):
            new_v = re.sub(r'^[✏\u270f\ufe0f]+\s*<b>', f'{EMOJI_RENAME_BUNDLE_TAG} <b>', new_v)

        # 8. bundle_deleted_success
        elif k == 'bundle_deleted_success':
            new_v = re.sub(r'^🗑\s*', f'{EMOJI_DELETE_TAG} ', new_v)

        # 9. edit_section_prompt
        elif k == 'edit_section_prompt':
            new_v = re.sub(r'^<b>[✏\u270f\ufe0f]+\s*', f'<b>{EMOJI_EDIT_TAG} ', new_v)

        # 10. statistics_menu_msg, statistics_empty_msg, generating_statistics_msg, statistics_image_caption
        elif k in ('statistics_menu_msg', 'statistics_empty_msg', 'generating_statistics_msg', 'statistics_image_caption'):
            new_v = re.sub(r'^📊\s*<b>', f'{EMOJI_STATISTIC_TAG} <b>', new_v)

        # 11. channel_action_msg, join_required_msg, scheduled_post_sent
        elif k in ('channel_action_msg', 'join_required_msg', 'scheduled_post_sent'):
            new_v = re.sub(r'^<b>📢\s*', f'<b>{EMOJI_CHANNEL_TAG} ', new_v)

        # 12. settings_channel_list_conf_msg, settings_mybots_msg
        elif k in ('settings_channel_list_conf_msg', 'settings_mybots_msg'):
            new_v = re.sub(r'^📢\s*<b>', f'{EMOJI_CHANNEL_TAG} <b>', new_v)

        # 13. inline_post_not_found
        elif k == 'inline_post_not_found':
            new_v = new_v.replace('❌', EMOJI_CLOSE_TAG)

        if new_v != old_v:
            d[k] = new_v
            changed_count += 1

    with open(filepath, 'w', encoding='utf-8') as fp:
        json.dump(d, fp, ensure_ascii=False, indent=4)
        fp.write('\n')

    print(f"Updated {filepath}: {changed_count} keys updated.")

def main():
    for f in sorted(glob.glob('language_packs/*.json')):
        update_file(f)

if __name__ == '__main__':
    main()
