#!/usr/bin/env python3
"""Resume one approved SHEIN request with original IDs/manifests/clock."""
import argparse
import json
from ares_campaign_v3.shein_continuation import run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--continuation',required=True)
    parser.add_argument('--confirm-execute',action='store_true')
    args=parser.parse_args()
    try:
        result=run(args.continuation,confirm_execute=args.confirm_execute)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except Exception as exc:
        # No raw exception/trace: transports may contain signed URLs.
        print(json.dumps({'status':'BLOCKED','stage':'same_id_continuation','error_type':type(exc).__name__}))
        return 2

if __name__=='__main__':raise SystemExit(main())
