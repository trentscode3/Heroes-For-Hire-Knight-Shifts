import argparse
import json

from core.balancing import (
    BalanceVariables,
    PlayerBalanceInput,
    report_to_dict,
    solve_for_target,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate balance settings for a target survival length.",
    )
    parser.add_argument("--games-played", type=int, required=True)
    parser.add_argument("--longest-employment", type=float, required=True)
    parser.add_argument("--expected-nights", type=float, required=True)
    parser.add_argument("--skill", type=float, required=True)
    parser.add_argument("--average-employment", type=float, default=0.0)
    parser.add_argument("--knights-killed", type=int, default=0)
    parser.add_argument("--archers-killed", type=int, default=0)
    parser.add_argument("--orcs-killed", type=int, default=0)
    parser.add_argument("--goliaths-killed", type=int, default=0)
    parser.add_argument("--shamans-killed", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    player = PlayerBalanceInput(
        games_played=args.games_played,
        longest_employment=args.longest_employment,
        expected_nights=args.expected_nights,
        skill=args.skill,
        average_employment=args.average_employment,
        knights_killed=args.knights_killed,
        archers_killed=args.archers_killed,
        orcs_killed=args.orcs_killed,
        goliaths_killed=args.goliaths_killed,
        shamans_killed=args.shamans_killed,
    )
    report = solve_for_target(player, BalanceVariables())
    data = report_to_dict(report)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return

    print(f"Predicted nights: {report.predicted_nights}")
    print(f"Target nights:    {report.target_nights}")
    print(f"Skill estimate:   {report.estimated_player_skill}")
    print("\nPlaytest spread:")
    for name, value in report.playtest_summary.items():
        print(f"  {name:8} {value:6.2f}")
    print("\nVariable weight in survival:")
    for name, weight in report.variable_weights.items():
        print(f"  {name:28} {weight:+.3f}")
    print("\nRecommended settings:")
    for name, value in report.recommended_settings.items():
        delta = report.recommendation_delta[name]
        print(f"  {name:28} {value:8.3f} ({delta:+.3f})")


if __name__ == "__main__":
    main()
