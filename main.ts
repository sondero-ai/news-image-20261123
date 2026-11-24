// Copies the finished page to the grader's output directory.
// Outside the grader, MAKEFUN_OUTPUT_DIR stands in for /output:
//   mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts

import { copyFile, mkdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, 'entry.png');
const outputDir = resolve(process.env.MAKEFUN_OUTPUT_DIR ?? '/output');
const target = join(outputDir, 'entry.png');

await mkdir(outputDir, { recursive: true });
await copyFile(source, target);

console.log(`entry.png -> ${target}`);
