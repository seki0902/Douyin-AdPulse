"""Open the plan-management page visibly and collect read-only calibration evidence."""
import json
import argparse

from browser_executor import BrowserInspector, ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan-id')
    parser.add_argument('--url', help='只读观察指定页面；不会写回执行配置')
    args = parser.parse_args()
    config = json.loads((ROOT / 'browser_execution_config.json').read_text(encoding='utf-8'))
    with BrowserInspector(args.url or config['url']) as inspector:
        print(json.dumps(inspector.observe(args.plan_id), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
