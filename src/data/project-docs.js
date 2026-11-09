// Seeded VIRA360 project data — a retail-fixture manufacturer running custom
// end-cap / display builds across US and China teams (mirrors the real domain).
//
// `thread` is the live conversation used by summarize/extract.
// `docs` are the "project history" corpus used by semantic search + the grounded
// assistant (both the managed KB and the local fallback RAG read this domain).

export const thread = `
[Rajesh] Client approved the end-cap display design but wants shelf depth reduced by 2 inches.
[Production] We need to confirm the hardware material by Friday or we miss the delivery date.
[Rajesh] US store rollout is now 120 locations, up from 90. Budget needs re-approval.
[QA] Last sample batch failed the paint-finish test and needs to be re-sprayed.
[Rajesh] Client wants a status update before their Monday board meeting.
`.trim();

// Each doc simulates a stored VIRA360 project record (chat digests, specs, QA logs).
export const docs = [
  {
    id: "proj-endcap-001",
    title: "End-cap display — design approval",
    text: "The client approved the end-cap display design for the spring rollout. One change requested: reduce shelf depth by 2 inches to fit narrower aisles. Design team to issue revised CAD by end of week.",
  },
  {
    id: "proj-endcap-002",
    title: "End-cap display — hardware material decision",
    text: "Production flagged that the mounting hardware material (brushed aluminum vs powder-coated steel) must be confirmed by Friday. Delay past Friday pushes the delivery date and risks the rollout schedule.",
  },
  {
    id: "proj-endcap-003",
    title: "Rollout scope change",
    text: "US store rollout expanded from 90 to 120 locations after the client added the Midwest region. This is a budget-impacting scope change and requires re-approval from the account sponsor before manufacturing scales up.",
  },
  {
    id: "proj-qa-014",
    title: "QA — paint finish failure",
    text: "The latest sample batch did not pass the finish-quality inspection. The coating showed uneven gloss and minor orange-peel texture. Batch must be re-sprayed and re-inspected before it ships to the client.",
  },
  {
    id: "proj-logistics-007",
    title: "China production — freight planning",
    text: "The China production team is coordinating ocean freight for the fixture components. Lead time is six weeks door-to-door; any hardware-material delay cascades directly into the freight booking window.",
  },
  {
    id: "proj-client-comms-003",
    title: "Client communications — board meeting",
    text: "The client requested a concise status update ahead of their Monday board meeting covering design sign-off, open approvals, and any schedule risk. Account team owns delivery of this update.",
  },
];
