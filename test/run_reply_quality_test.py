import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.llm_helper import LLMHelper  # noqa: E402


@dataclass
class SamplePost:
    sample_id: int
    author: str
    handle: str
    lane: str
    text: str


SAMPLE_POSTS: List[SamplePost] = [
    SamplePost(
        sample_id=1,
        author="Bonafide Brand",
        handle="everythingfxx",
        lane="journal_intent",
        text=(
            "If you need a LOAN to trade, you need discipline. Trading with borrowed money adds pressure, "
            "kills plan execution, triggers revenge trades, and the market does not care about repayment dates."
        ),
    ),
    SamplePost(
        sample_id=2,
        author="Ariyan + Cooper thread",
        handle="daaniyaan",
        lane="broad_trending",
        text=(
            "I used to build with AI in 2023, then stopped for about a year while life got unstable. "
            "Now I feel behind and want to get back in. A reply said progress has been massive recently."
        ),
    ),
    SamplePost(
        sample_id=3,
        author="unusual_whales",
        handle="unusual_whales",
        lane="broad_trending",
        text="Powell said inflation for goods has picked up, reflecting the effect of tariffs.",
    ),
    SamplePost(
        sample_id=4,
        author="Bitget + pandavishnu8 HUDL thread",
        handle="pandavishnu08",
        lane="journal_intent",
        text=(
            "Trading competitions attract participation, but risk management still determines survival."
        ),
    ),
    SamplePost(
        sample_id=5,
        author="Spencer Hakimian",
        handle="SpencerHakimian",
        lane="broad_trending",
        text="This is a recession.",
    ),
    SamplePost(
        sample_id=6,
        author="Alpha Capital Group",
        handle="AlphaCapitalUK",
        lane="journal_intent",
        text=(
            "5 evals passed, 5.5K withdrawn, 65% win rate, but still inconsistent. "
            "One account was opened and finished next day because of forced setups."
        ),
    ),
    SamplePost(
        sample_id=7,
        author="CGTN America",
        handle="cgtnamerica",
        lane="broad_trending",
        text="DOW closed -1.34%, S&P 500 -1.57%, NASDAQ -2.03%.",
    ),
    SamplePost(
        sample_id=8,
        author="Claudia Rea",
        handle="_claudiarea",
        lane="journal_intent",
        text=(
            "Real-time journaling is far better than writing everything days later because you lose emotional context, "
            "impulses, and true reasons for entries. Psychology is a major edge."
        ),
    ),
    SamplePost(
        sample_id=9,
        author="Market Mind Truth",
        handle="MarketMindTruth",
        lane="journal_intent",
        text=(
            "People blow accounts on XAUUSD with no stop loss, oversized positions, manual close plans, and revenge trades. "
            "Volatility without risk control is a faster way to lose."
        ),
    ),
    SamplePost(
        sample_id=10,
        author="iamlpt_forex",
        handle="I_Am_LPT",
        lane="journal_intent",
        text=(
            "Why do people stay in trading after losses: sunk cost, addiction, belief in potential, no other option, or lifestyle?"
        ),
    ),
]


def _build_settings(model_name: str) -> dict:
    return {
        "twitter_automation": {
            "action_config": {
                "llm_settings_for_reply": {
                    "model_name_override": model_name,
                }
            }
        }
    }


async def _generate_replies(
    llm: LLMHelper,
    posts: List[SamplePost],
    variations: int,
    pause_seconds: float,
    per_reply_timeout_seconds: float,
) -> List[str]:
    lines: List[str] = []
    for post in posts:
        print(
            f"[sample {post.sample_id}/{len(posts)}] @{post.handle} lane={post.lane} -> generating {variations} replies..."
        )
        lines.append(
            f"===== SAMPLE {post.sample_id}: {post.author} (@{post.handle}) | lane={post.lane} ====="
        )
        lines.append("SOURCE:")
        lines.append(post.text)
        lines.append("")
        lines.append("REPLIES:")

        for i in range(variations):
            try:
                print(f"  - variation {i + 1}/{variations}")
                reply = await asyncio.wait_for(
                    llm.generate_reply(
                        tweet_text=post.text,
                        user_handle=post.handle,
                        lane_name=post.lane,
                    ),
                    timeout=per_reply_timeout_seconds,
                )
                reply = (reply or "").strip()
                if not reply:
                    reply = "[EMPTY]"
            except asyncio.TimeoutError:
                reply = "[TIMEOUT] Reply generation exceeded timeout"
            except asyncio.CancelledError:
                lines.append(f"{i + 1}. [CANCELLED] run interrupted by user")
                lines.append("")
                return lines
            except Exception as exc:
                reply = f"[ERROR] {exc}"

            lines.append(f"{i + 1}. {reply}")
            if pause_seconds > 0:
                await asyncio.sleep(pause_seconds)

        lines.append("")

    return lines


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Local reply quality runner for LynxTrades engagement prompts."
    )
    parser.add_argument(
        "--output",
        default=str(Path("test") / "output.txt"),
        help="Output file path for generated replies.",
    )
    parser.add_argument(
        "--variations",
        type=int,
        default=3,
        help="How many replies to generate for each sample post.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.3,
        help="Delay between API calls.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("XAI_TEST_MODEL", "grok-4-1-fast-reasoning"),
        help="Grok model name override.",
    )
    parser.add_argument(
        "--reply-timeout-seconds",
        type=float,
        default=float(os.getenv("REPLY_TEST_TIMEOUT_SECONDS", "45")),
        help="Per reply timeout (async wait_for) in seconds.",
    )
    parser.add_argument(
        "--xai-timeout-seconds",
        type=int,
        default=int(os.getenv("XAI_TIMEOUT_SECONDS", "45")),
        help="HTTP timeout passed to Grok API calls.",
    )
    parser.add_argument(
        "--use-env-proxy",
        action="store_true",
        help="Use HTTP(S)_PROXY environment variables for xAI requests.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    os.environ["XAI_TIMEOUT_SECONDS"] = str(max(10, args.xai_timeout_seconds))
    os.environ["XAI_DISABLE_ENV_PROXY"] = "false" if args.use_env_proxy else "true"

    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not os.getenv("XAI_API_KEY"):
        output_path.write_text(
            "Missing XAI_API_KEY. Add it to your .env, then run:\n"
            "python test/run_reply_quality_test.py\n",
            encoding="utf-8",
        )
        print(f"Wrote setup warning to {output_path}")
        return 1

    settings = _build_settings(args.model)
    llm = LLMHelper(settings=settings)

    lines: List[str] = [
        "LynxTrades Reply Quality Test",
        f"Generated at (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"Model: {llm.model_name}",
        f"Variations per sample: {args.variations}",
        f"Per reply timeout (s): {max(5.0, args.reply_timeout_seconds)}",
        f"HTTP timeout (s): {max(10, args.xai_timeout_seconds)}",
        f"Use env proxy: {args.use_env_proxy}",
        "",
    ]
    interrupted = False
    try:
        lines.extend(
            await _generate_replies(
                llm=llm,
                posts=SAMPLE_POSTS,
                variations=max(1, args.variations),
                pause_seconds=max(0.0, args.pause_seconds),
                per_reply_timeout_seconds=max(5.0, args.reply_timeout_seconds),
            )
        )
    except asyncio.CancelledError:
        interrupted = True
        lines.append("")
        lines.append("[INTERRUPTED] Run was cancelled before completion.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote reply quality output to {output_path}")
    if interrupted:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
