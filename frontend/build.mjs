// Bundle the browser code into static/dist/app.js with esbuild.
import * as esbuild from "esbuild"

const watch = process.argv.includes("--watch")

const options = {
  entryPoints: ["frontend/src/app.ts"],
  bundle: true,
  format: "esm",
  target: ["es2022"],
  outfile: "static/dist/app.js",
  sourcemap: true,
  minify: !watch,
  legalComments: "linked",
  logLevel: "info",
}

if (watch) {
  const context = await esbuild.context(options)
  await context.watch()
} else {
  await esbuild.build(options)
}
