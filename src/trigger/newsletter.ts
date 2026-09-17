import { schedules, logger } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";

// Runs the full Monk10x newsletter pipeline every Tuesday and Thursday at 9:00 AM IST.
//
// All orchestration logic lives in Python (tools/run_scheduled_issue.py) - this task is a
// thin scheduler + invoker, not where the pipeline logic lives. See that script's docstring
// and workflows/newsletter_automation.md for what it does.
//
// By design, each run emails a review-only draft to Kislay (kislayranjan@gmail.com) - it does
// NOT bcc the real subscriber list. That's a deliberate safety choice (unreviewed LLM content
// shouldn't go straight to subscribers) - see workflows/newsletter_automation.md before
// changing this.
export const monk10xNewsletterIssue = schedules.task({
  id: "monk10x-newsletter-issue",
  cron: {
    pattern: "0 9 * * 2,4",
    // "Asia/Kolkata" is the current, correct IANA identifier for IST, but Trigger.dev's
    // deploy-time validator rejected it ("Invalid IANA timezone") on 2026-09-17 - looks like
    // their supported-timezone list hasn't caught up to the IANA rename yet. "Asia/Calcutta"
    // is the older alias for the exact same zone (UTC+5:30, no DST) via the tzdata Link table,
    // and deploys successfully. If a future Trigger.dev update adds "Asia/Kolkata" support,
    // switching back is cosmetic only - same actual schedule either way.
    timezone: "Asia/Calcutta",
  },
  maxDuration: 600,
  run: async () => {
    logger.info("Starting Monk10x scheduled newsletter run");

    const result = await python.runScript("./tools/run_scheduled_issue.py");

    logger.info("Pipeline stdout", { stdout: result.stdout });
    if (result.stderr) {
      logger.warn("Pipeline stderr", { stderr: result.stderr });
    }

    if (result.exitCode !== 0) {
      throw new Error(
        `run_scheduled_issue.py exited with code ${result.exitCode}:\n${result.stderr}`
      );
    }

    return { summary: result.stdout };
  },
});
