// Board page: load a bank position, let the player move, then show the verdict and the
// acceptable moves (specs/move_acceptance_spec.md §8). All scores come from the server.
import { Chessground } from "https://cdn.jsdelivr.net/npm/chessground@9.2.1/dist/chessground.js";

const $ = (id) => document.getElementById(id);
const BRUSHES = ["green", "blue", "yellow"]; // arrows for acceptable moves #1, #2, #3
const MORE_BRUSH = "paleGreen"; // the rest of the acceptable set, with "show all"
const SECOND_BRUSH = "red"; // the 2nd-best move in an only-move position: NOT acceptable

let cg = null;
let position = null;
let result = null;

function formatScore(m) {
  // Scores are from the mover's point of view (the side to move).
  if (m.score_mate !== null) return m.score_mate > 0 ? `mate in ${m.score_mate}` : `mated in ${-m.score_mate}`;
  const pawns = m.score_cp / 100;
  return (pawns > 0 ? "+" : "") + pawns.toFixed(2);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

const arrow = (m, brush) => ({ orig: m.uci.slice(0, 2), dest: m.uci.slice(2, 4), brush });

async function loadPosition() {
  // ?id=123 in the page URL serves that bank position (handy for checking one).
  const id = new URLSearchParams(location.search).get("id");
  const res = await fetch(id ? `/api/position?id=${encodeURIComponent(id)}` : "/api/position");
  const data = await res.json();
  if (!res.ok) {
    $("prompt").textContent = `Error: ${data.detail}`;
    return;
  }
  position = data;
  result = null;

  $("result").hidden = true;
  $("result").innerHTML = "";
  $("show-all-label").hidden = true;
  $("show-all").checked = false;
  $("only-move").checked = false;
  $("only-move").disabled = false;

  $("meta").textContent = [position.phase, position.opening].filter(Boolean).join(" · ");
  $("prompt").textContent = `${position.turn === "white" ? "White" : "Black"} to move.`;

  const config = {
    fen: position.fen,
    orientation: position.turn,
    turnColor: position.turn,
    lastMove: undefined,
    movable: {
      free: false,
      color: position.turn,
      dests: new Map(Object.entries(position.dests)),
      showDests: true,
      events: { after: onMove },
    },
    drawable: { autoShapes: [] },
  };
  if (cg) cg.set(config);
  else cg = Chessground($("board"), config);
}

async function onMove(orig, dest) {
  cg.set({ movable: { color: undefined, dests: new Map() } }); // lock the board
  $("only-move").disabled = true;
  $("result").hidden = false;
  $("result").textContent = "Checking…";

  const res = await fetch("/api/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ position_id: position.id, move: orig + dest, only_move: $("only-move").checked }),
  });
  const data = await res.json();
  if (!res.ok) {
    $("result").textContent = `Error: ${data.detail}`;
    return;
  }
  result = data;
  showResult();
}

function drawArrows() {
  const showAll = $("show-all").checked;
  const moves = showAll ? result.acceptable : result.arrows;
  const shapes = moves.map((m, i) => arrow(m, BRUSHES[i] ?? MORE_BRUSH));
  if (result.second_best) shapes.push(arrow(result.second_best, SECOND_BRUSH));
  cg.setAutoShapes(shapes);
}

function showResult() {
  const v = result.verdict;
  const rows = result.arrows
    .map((m, i) => `<li class="${BRUSHES[i]}"><b>${escapeHtml(m.san)}</b> ${formatScore(m)}</li>`)
    .join("");
  const second = result.second_best
    ? `<p class="second">Red arrow, not acceptable: <b>${escapeHtml(result.second_best.label)}</b>
       (${formatScore(result.second_best)}).</p>`
    : "";
  const claim = result.only_move_claim ? "You said: only good move." : "You said: not an only-move position.";

  $("result").innerHTML = `
    <p class="verdict ${v.acceptable ? "good" : "bad"}"><b>${escapeHtml(v.san)}</b>: ${escapeHtml(v.text)}</p>
    <p class="small">Your move: ${formatScore(result.player)}</p>
    <p>${escapeHtml(result.count_text)}.</p>
    <ol class="top">${rows}</ol>
    ${second}
    <p class="small">${claim}</p>`;

  const more = result.acceptable.length > result.arrows.length;
  $("show-all-label").hidden = !more;
  $("show-all-text").textContent = `Show all ${result.acceptable.length} acceptable moves`;
  drawArrows();
}

$("show-all").addEventListener("change", () => result && drawArrows());
$("next").addEventListener("click", () => {
  if (location.search) history.replaceState(null, "", location.pathname); // leave ?id= behind
  loadPosition();
});
loadPosition();
