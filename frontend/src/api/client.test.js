import { describe, expect, it } from "vitest";
import { parseJson, wrapNetworkError } from "./client.js";

describe("wrapNetworkError", () => {
  it("rewrites TypeError into flask-on-5050 hint", () => {
    expect(() => wrapNetworkError(new TypeError("Failed to fetch"))).toThrow(
      /port 5050/
    );
  });

  it("rewrites failed to fetch strings", () => {
    expect(() => wrapNetworkError(new Error("Failed to fetch"))).toThrow(
      /flask server running on port 5050/
    );
  });

  it("rethrows other errors", () => {
    expect(() => wrapNetworkError(new Error("ticker must be valid"))).toThrow(
      "ticker must be valid"
    );
  });
});

describe("parseJson", () => {
  it("returns body on ok", async () => {
    const res = {
      ok: true,
      text: async () => JSON.stringify({ ok: true }),
    };
    const data = await parseJson(res);
    expect(data.ok).toBe(true);
  });

  it("throws server error message", async () => {
    const res = {
      ok: false,
      statusText: "Bad Request",
      text: async () => JSON.stringify({ error: "fast period must be smaller" }),
    };
    await expect(parseJson(res)).rejects.toThrow(/fast period/);
  });
});
