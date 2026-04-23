const fcPaths = ["C:\\Veritas_Lab\\test_file.txt", "C:\\\\Veritas_Lab\\\\test_file.txt"];
for (const p of fcPaths) {
  const fc = { args: { path: p, content: "This is a test file." } };
  const str = JSON.stringify(fc.args).replace(/"/g, '\\"');
  let cleaned = str.replace(/\\"/g, '"');
  try {
    const obj = JSON.parse(cleaned);
    console.log("Success with path length " + p.length + ":", obj.path);
  } catch (e) {
    console.error("FAIL with path length " + p.length + ":", e.message);
  }
}
