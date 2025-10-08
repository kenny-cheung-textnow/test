// server_after.js
import express from "express";
import { z } from "zod";
import xss from "xss";

const app = express();
app.use(express.json());

const CommentSchema = z.object({
  postId: z.string().uuid(),
  text: z.string().min(1).max(2000),
});

function violatesPolicy(t) {
  const s = t.toLowerCase();
  return s.includes("kill") || s.includes("doxx") || s.includes("ransomware");
}

app.post("/comment", async (req, res) => {
  const parsed = CommentSchema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: "bad_request" });

  const clean = xss(parsed.data.text);
  if (violatesPolicy(clean)) return res.status(400).json({ error: "policy_blocked" });

  await db.insert({ postId: parsed.data.postId, text: clean });
  res.json({ ok: true });
});
app.listen(3000);
