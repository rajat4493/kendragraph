import argparse, json, datetime as dt
from dateutil.relativedelta import relativedelta
from .validator_service import run_validation

def iso(s): return dt.datetime.fromisoformat(s.replace("Z","+00:00"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", help="ISO start (UTC), e.g., 2025-11-08T00:00:00Z")
    ap.add_argument("--end", help="ISO end (UTC)")
    ap.add_argument("--days", type=int, default=0, help="If provided, use now-<days> .. now")
    ap.add_argument("--tca-window-s", type=int, default=300)
    ap.add_argument("--dist-window-km", type=float, default=1.0)
    args = ap.parse_args()

    if args.days > 0:
        end = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
        start = end - relativedelta(days=args.days)
    else:
        start, end = iso(args.start), iso(args.end)

    res = run_validation(start, end, args.tca_window_s, args.dist_window_km)
    print(json.dumps(res, default=str, indent=2))

if __name__ == "__main__":
    main()
