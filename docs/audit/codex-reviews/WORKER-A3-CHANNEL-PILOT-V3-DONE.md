verdict: AGREE

issue-1-fixed: yes

channel-panel-keys-8-keys: verified yes

remaining concerns:
- Non-blocking: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1369` comment still says `CHANNEL_PANEL_KEYS 7 keys`.
- Non-blocking: `agent_channel/api.py:214` comment still says done event panels 7 keys.
- Caveat: `ConversationPanel` still renders via separate `messages` state, but V3 now hydrates `conversation` in `normalizeBackendDone()` and immediately syncs `setMessages(live.conversation)`, so this satisfies the stated OR condition.

Verified against commit `5876b7b`, not the current checkout, which is on `main` at `16127bb` with unrelated unresolved doc conflicts.

Evidence:
- `shared/sse_envelope.py` defines `CHANNEL_PANEL_KEYS` with 8 keys including `"conversation"`.
- `agent_channel/realtime_stream.py` emits `"conversation": []` in live `make_done(panels=...)`.
- `agent_channel/api.py` demo endpoint emits `"conversation": data.get("conversation", [])`.
- `ChannelWorkspace.tsx` `normalizeBackendDone()` now reads `evt.conversation` and returns it in the `ChannelSession`.
- `QueryBar` calls `setLiveData(live)` and `setMessages(live.conversation)` for both real search and demo.
- Playwright T6 injects a sentinel backend `conversation` turn and asserts `[data-testid="channel-pilot-conversation"]` contains it.

Net: the V2 partial gap is addressed. The panel is not directly rendered from `sessionData.conversation`, but the done-envelope hydration path is now real and covered by a regression test.