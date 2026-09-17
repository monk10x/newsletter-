import { defineConfig } from "@trigger.dev/sdk";
import { pythonExtension } from "@trigger.dev/python/extension";
import { syncEnvVars } from "@trigger.dev/build/extensions/core";
import fs from "node:fs";

// Reads the local Gmail/Drive OAuth secrets (credentials.json/token.json - both gitignored,
// never committed) and pushes them as Trigger.dev secrets on every deploy, so they never
// need to be manually copy-pasted into the dashboard. See tools/google_auth.py and
// workflows/newsletter_automation.md for what these are for.
function readGoogleOAuthSecrets(): Record<string, string> {
  const credentials = JSON.parse(fs.readFileSync("./credentials.json", "utf-8"));
  const installed = credentials.installed ?? credentials.web;
  const token = JSON.parse(fs.readFileSync("./token.json", "utf-8"));
  return {
    GOOGLE_CLIENT_ID: installed.client_id,
    GOOGLE_CLIENT_SECRET: installed.client_secret,
    GOOGLE_REFRESH_TOKEN: token.refresh_token,
  };
}

export default defineConfig({
  project: "proj_pepznhnlutbgiphxjbsv",
  runtime: "node-24",
  logLevel: "log",
  // The max compute seconds a task is allowed to run. If the task run exceeds this duration, it will be stopped.
  // You can override this on an individual task.
  // See https://trigger.dev/docs/runs/max-duration
  maxDuration: 3600,
  retries: {
    enabledInDev: true,
    default: {
      maxAttempts: 3,
      minTimeoutInMs: 1000,
      maxTimeoutInMs: 10000,
      factor: 2,
      randomize: true,
    },
  },
  dirs: ["./src/trigger"],
  build: {
    extensions: [
      // The actual newsletter pipeline is Python (tools/*.py) - this installs it and its
      // requirements into the build image so python.runScript() can call it. See
      // tools/run_scheduled_issue.py and workflows/newsletter_automation.md.
      pythonExtension({
        scripts: ["./tools/**/*.py"],
        requirementsFile: "./requirements.txt",
      }),
      syncEnvVars(async () => ({
        ...readGoogleOAuthSecrets(),
        ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY ?? "",
        TAVILY_API_KEY: process.env.TAVILY_API_KEY ?? "",
        KIE_API_KEY: process.env.KIE_API_KEY ?? "",
      })),
    ],
  },
});
