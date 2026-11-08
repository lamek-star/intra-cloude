import { describe, expect, it } from "vitest";
import {
  base64urlToBuffer,
  bufferToBase64url,
  credentialToJson,
  passkeyErrorMessage,
  toCreationOptions,
  toRequestOptions,
} from "./passkeys";

const bytes = (...b: number[]) => new Uint8Array(b).buffer;

describe("passkey conversions", () => {
  it("round-trips base64url without padding, including the URL-safe characters", () => {
    const value = bytes(0xfb, 0xff, 0xbf, 0x00, 0x01);
    const text = bufferToBase64url(value);
    expect(text).toBe("-_-_AAE");
    expect(new Uint8Array(base64urlToBuffer(text))).toEqual(new Uint8Array(value));
  });

  it("turns the server's creation options into the buffers the browser wants, keeping the hints", () => {
    const options = toCreationOptions({
      challenge: "AAEC",
      rp: { id: "localhost", name: "IntraForge" },
      user: { id: "AQID", name: "owner@shop.test", displayName: "Owner" },
      excludeCredentials: [{ id: "BAUG", type: "public-key" }],
      hints: ["hybrid"],
    });
    expect(new Uint8Array(options.challenge as ArrayBuffer)).toEqual(new Uint8Array([0, 1, 2]));
    expect(new Uint8Array(options.user.id as ArrayBuffer)).toEqual(new Uint8Array([1, 2, 3]));
    expect(new Uint8Array(options.excludeCredentials![0].id as ArrayBuffer)).toEqual(new Uint8Array([4, 5, 6]));
    expect((options as unknown as { hints: string[] }).hints).toEqual(["hybrid"]);
  });

  it("leaves an empty allow list for a sign-in that names nobody", () => {
    const options = toRequestOptions({ challenge: "AAEC", rpId: "localhost", allowCredentials: [] });
    expect(options.allowCredentials).toEqual([]);
  });

  it("writes an assertion as the JSON the server reads", () => {
    const credential = {
      id: "AQID",
      rawId: bytes(1, 2, 3),
      type: "public-key",
      response: { clientDataJSON: bytes(9), authenticatorData: bytes(8), signature: bytes(7), userHandle: bytes(6) },
      getClientExtensionResults: () => ({}),
    } as unknown as PublicKeyCredential;
    expect(credentialToJson(credential)).toEqual({
      id: "AQID",
      rawId: "AQID",
      type: "public-key",
      response: { clientDataJSON: "CQ", authenticatorData: "CA", signature: "Bw", userHandle: "Bg" },
      clientExtensionResults: {},
    });
  });

  it("writes a new passkey with its transports", () => {
    const credential = {
      id: "AQID",
      rawId: bytes(1, 2, 3),
      type: "public-key",
      response: { clientDataJSON: bytes(9), attestationObject: bytes(5), getTransports: () => ["hybrid"] },
      getClientExtensionResults: () => ({}),
    } as unknown as PublicKeyCredential;
    expect(credentialToJson(credential).response).toEqual({ clientDataJSON: "CQ", attestationObject: "BQ", transports: ["hybrid"] });
  });

  it("explains browser refusals in words", () => {
    expect(passkeyErrorMessage(new DOMException("x", "NotAllowedError"))).toMatch(/closed or timed out/);
    expect(passkeyErrorMessage(new DOMException("x", "SecurityError"))).toMatch(/by its name/);
    expect(passkeyErrorMessage(new Error("other"))).toBeNull();
  });
});
