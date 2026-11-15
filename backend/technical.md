Feature: Technical Queries

under the individual pipeline add a technical button.

what it does is instead of directly sending the prompt to illicit a response, first clarify the prompt by rewriting it in a logically clear way, eliminate any ambiguities by stating what it understood by the prompt, stating the tacit assumptions, assumptions made about the backgroud/context and allowing the user to review and alter it to make sure that we are on the same page.

the way I see it implemented is that you get a technical button in the individual tab.
when pressed/switched on then the prompt you give goes through the technical pipeline first, the pipeline sends the prompt to an llm which will just work to restate the prompt in a technically sound and clear wording, elininate ambiguities introduced by unclear working etc, state the assumed context, assumptions about depth of the question and at what depth an answer is expected.

then the benedicted/cured prompt is returned for a final review in which we ask the user if we got it right and allow any changes if required before finally sending it to the normal individual pipeline which generates the actual response

Architectural considerations

- This feature is for the research-topic pipeline, not the PDF-based Individual pipeline described above.
- Keep the existing research flow unchanged when Technical mode is off.
- When Technical mode is on, run a separate LLM rewrite step first. Return its interpretation as an editable draft; the user can accept it or make changes before research starts.
- Keep the rewrite step modular and separate from the existing research pipeline. Do not add a clarification follow-up or question-and-answer loop.
- Send the final user-approved prompt through the existing research pipeline for answer generation.
- Leave conversation history and its storage behavior unchanged. The history should contain the prompt actually sent to research, whether it is the original prompt or the user-approved rewrite; do not add a separate history entry for the original prompt or rewrite draft.

Implementation steps

1. Add an optional Technical mode toggle to the Research interface. When off, keep the current research flow unchanged.
2. Add an authenticated backend endpoint that accepts the original prompt and returns an LLM-rewritten draft. Keep this rewrite step separate from the existing research pipeline.
3. Show the returned draft in an editable review step. The user can edit and approve it, or return to the original prompt. Do not start research before approval.
4. On approval, send the final prompt through the existing research endpoint and pipeline. Do not change the report-generation pipeline for this feature.
5. Keep conversation history behavior unchanged: save only the final prompt sent to research and the resulting report. Do not save the original prompt or rewrite draft as additional messages.
6. Verify that normal mode still works, Technical mode waits for approval, edits are what research receives and history saves, and cancellation or rewrite failure does not create history entries.
