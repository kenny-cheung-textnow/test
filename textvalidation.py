// server_before.js
import express from "express";
const app = express();
app.use(express.json());

app.post("/comment", async (req, res) => {
  const { postId, text } = req.body; // no validation, no sanitization
  await db.insert({ postId, text });
  res.json({ ok: true });
});
app.listen(3000);
