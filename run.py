"""Soccer prediction model — entry point."""
import sys
import os
import yaml


def cmd_backtest():
    from backtest.engine import run_backtest
    from backtest.metrics import compute_metrics, print_metrics_report

    with open('config/leagues.yaml', 'r') as f:
        config = yaml.safe_load(f)

    predictions_df = run_backtest(
        ratings_path='data/processed/ratings.csv',
        merged_path='data/processed/all_merged.csv',
        leagues_config_path='config/leagues.yaml',
        output_path='output/backtest_results/predictions.csv'
    )

    metrics = compute_metrics(predictions_df)
    report = print_metrics_report(metrics)

    # Save text report
    report_path = 'output/backtest_results/metrics_report.txt'
    os.makedirs('output/backtest_results', exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to {report_path}")


def cmd_predict():
    print("Live predictions coming in Phase 3")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <command>")
        print("Commands:")
        print("  backtest   Run historical backtest and print metrics")
        print("  predict    (Phase 3) Generate live match predictions")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == 'backtest':
        cmd_backtest()
    elif command == 'predict':
        cmd_predict()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
