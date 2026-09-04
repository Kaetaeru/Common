/* Run web/solver.js over a config matrix and print the results as JSON.
 * test_solver_parity.py runs the Python solver over the same matrix and diffs. */

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { apuGenerateSchedules } = require(join(here, "..", "web", "solver.js"));

const [, , dataPath, configPath] = process.argv;
const data = JSON.parse(readFileSync(dataPath, "utf-8"));
const configs = JSON.parse(readFileSync(configPath, "utf-8"));

const out = configs.map((config) => {
  const result = apuGenerateSchedules(data, config);
  return {
    errors: result.errors,
    results: result.results.map((r) => ({
      label: r.label,
      score: r.score,
      credits: r.credits,
      codes: r.courses.map((c) => String(c.classCode)).sort(),
      metrics: r.metrics,
      explanations: r.explanations,
      warnings: r.warnings,
    })),
  };
});

process.stdout.write(JSON.stringify(out, null, 2));
