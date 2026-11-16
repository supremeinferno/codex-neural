Feature: Technical Queries (implemented)

Technical mode belongs to the web Research interface, not the PDF Individual
pipeline. When enabled, the original topic is sent to a separate LLM rewrite
endpoint. The returned interpretation is shown as an editable draft; research
starts only after the user approves it. The approved text then goes through the
existing research pipeline.

Architectural considerations

- This feature is for the research-topic pipeline, not the PDF-based Individual pipeline described above.
- Keep the existing research flow unchanged when Technical mode is off.
- When Technical mode is on, run a separate LLM rewrite step first. Return its interpretation as an editable draft; the user can accept it or make changes before research starts.
- Keep the rewrite step modular and separate from the existing research pipeline. Do not add a clarification follow-up or question-and-answer loop.
- Send the final user-approved prompt through the existing research pipeline for answer generation.
- Leave conversation history and its storage behavior unchanged. The history should contain the prompt actually sent to research, whether it is the original prompt or the user-approved rewrite; do not add a separate history entry for the original prompt or rewrite draft.

Implementation checklist (completed)

1. Added an optional Technical mode toggle to the Research interface; normal mode keeps the direct flow.
2. Added an authenticated rewrite endpoint separate from the existing research pipeline.
3. Added an editable review step; research starts only after approval.
4. Sends the approved prompt through the existing research endpoint and pipeline.
5. Keeps history unchanged: only the final prompt and resulting report are saved.
6. Verified normal and Technical mode behavior, including approval before research and no history entry during rewrite.
