"""Read the budget editor's real DOM without changing or submitting a value."""
import argparse
import json

from browser_executor import BrowserInspector, ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-id', required=True)
    args = parser.parse_args()
    config = json.loads((ROOT / 'browser_execution_config.json').read_text(encoding='utf-8'))
    url = config['url'].replace('/ad?', '/project?')
    with BrowserInspector(url) as inspector:
        page = inspector.page
        page.wait_for_timeout(15000)
        row = page.locator('tr').filter(has_text=f'ID: {args.project_id}')
        if row.count() != 1:
            raise RuntimeError('目标项目行未唯一定位')
        edit = row.locator('td').nth(5).locator("iconpark-icon[name='oc-icon-edit']")
        if edit.count() != 1:
            raise RuntimeError('预算编辑图标未唯一定位')
        row.hover(timeout=10000)
        edit.click(timeout=10000)
        page.wait_for_timeout(500)
        visible = page.locator('.ovui-popover:visible, .ovui-modal:visible, .ovui-dialog:visible')
        inputs = page.locator('input:visible')
        result = {
            'body': page.locator('body').inner_text(),
            'project_id': args.project_id,
            'editor_count': visible.count(),
            'editor_html': visible.first.inner_html() if visible.count() == 1 else None,
            'visible_inputs': [
                {'type': inputs.nth(i).get_attribute('type'), 'value': inputs.nth(i).input_value(),
                 'placeholder': inputs.nth(i).get_attribute('placeholder'), 'class': inputs.nth(i).get_attribute('class')}
                for i in range(inputs.count())
            ],
        }
        directory = ROOT / 'output' / 'playwright' / 'inspection'
        directory.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(directory / 'budget-editor.png'), full_page=True)
        (directory / 'budget-editor.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
