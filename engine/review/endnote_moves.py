"""Revision plans for delivered diagnoses; separate from margin-comment prose.

Each plan expands the next step for that particular diagnosis. Anchors are
student text, not invented examples, and no template adds another diagnosis.
"""

PRIORITY_PLANS = {
    'acronym_case': (
        'Check the abbreviation marked at {anchor} against the full term you introduce in the draft. '
        'Use the same capitalized form in your own discussion after defining it. Treat this as a '
        'consistency check across the paper, while preserving the wording of quotations and source '
        'titles. An abbreviation should help readers recognize the same term each time it appears.'),
    'typo_cluster': (
        'The passage marked at {anchor} is one example from the punctuation and spacing check. '
        'Work through the individual specimens in the margin, keeping the corrected sentence beside '
        'its original while you check the meaning. Then make a separate pass for similar slips '
        'elsewhere in the draft. Keep source wording intact when checking quotations, and avoid changing an unfamiliar form without verifying it.'),
    'repeated_opener': (
        'Read the paragraph beginning {anchor} alongside the opening immediately before it. '
        'The repeated construction is a reason to check whether each opening identifies its own '
        'point clearly. Where a revision would help, build the connection from the ideas being '
        'discussed. You can retain repeated wording when it expresses a useful parallel; an arbitrary synonym would not improve that relationship.'),
    'thesis_long': (
        'The thesis at {anchor} needs a decision about what belongs in the central claim. '
        'Keep the position you will establish and the main points that lead to it. Move explanations '
        'that need their own evidence into the body, then read the shorter thesis alongside the '
        'paragraph openings. It should still represent the argument accurately after you have removed the extra detail.'),
    'thesis_vague': (
        'Return to {anchor} when revising the thesis. Decide which relationship between the ideas '
        'the paper will explain, and state it in terms that fit the discussion you have written. '
        'Then compare that sentence with the main point of each body paragraph. Keep the points '
        'that help establish the claim; revise the wording where the promise and discussion differ.'),
    'thesis_missing': (
        'The introduction currently reaches {anchor} without a clear statement of the essay’s position. '
        'Before rewriting it, make a brief list of the points developed in the body. What conclusion '
        'do those points support together? Use that answer to form the central claim, then place it '
        'where the opening moves from introducing the subject to setting out your argument.'),
    'thesis_no_preview': (
        'Use the claim at {anchor} to check the direction promised by the introduction. Identify the '
        'main points developed in the body and decide which ones readers need to know at the outset. '
        'Build those points into the thesis in the order you discuss them. The preview should show '
        'the route through the argument without listing every supporting example.'),
    'paragraph_overlong': (
        'Look again at the section containing {anchor}. Give the paragraph a short working label '
        'that states its main point, then test each sentence against that label. Keep the explanation '
        'and evidence for that point together. Where a different point begins, consider a paragraph '
        'break and a new opening sentence. Length alone does not require a split; the change of focus should guide it.'),
    'conclusion_summary': (
        'Use {anchor} as a starting point for revising the ending. The body has already taken readers '
        'through the individual points, so consider what they mean when read together. Choose one '
        'connection that the discussion supports and explain its significance. Keep that final reflection '
        'within the argument already developed, rather than adding a separate issue that the body has not examined.'),
    'conclusion_thin': (
        'The closing passage at {anchor} needs room to bring the discussion together. Identify the '
        'connection between the body’s main points before extending the paragraph. Explain what that '
        'connection helps readers understand about the subject. This gives the ending a purpose beyond '
        'naming the points again and keeps the final thought tied to the work the essay has done.'),
    'conclusion_new_evidence': (
        'The claim marked at {anchor} needs a decision about where it belongs. If it is necessary '
        'to your argument, introduce its supporting evidence in the body and explain the reasoning there. '
        'Otherwise, leave it out of the ending. Use the final paragraph to draw a conclusion from '
        'the material readers have already had an opportunity to consider.'),
    'claim_scope_support': (
        'For the statement at {anchor}, separate what your evidence establishes from what you infer. '
        'Look at the group or outcome described: does the source or example justify the full extent '
        'of the claim? Add the supporting evidence where it is needed, or narrow the statement. '
        'Readers should be able to follow the reasoning without being asked to accept a broader generalization.'),
    'evidence_no_analysis': (
        'Revisit the source passage marked at {anchor}. Write down the point this evidence is meant '
        'to support, then identify the detail in the source that helps establish it. Put that reasoning '
        'beside the evidence in the paragraph. This explanation is your contribution: it tells readers '
        'how the source advances the argument instead of leaving them to make that connection on their own.'),
    'reading_response_link': (
        'The response at {anchor} would be easier to follow with a closer explanation of the source. '
        'Choose the particular words or findings that led you to this interpretation and discuss them '
        'before extending your response. Distinguish the source’s statement from your conclusion so '
        'readers can see both what you are responding to and how you arrived at your own position.'),
    'transition_abrupt': (
        'Check the move into {anchor} beside the end of the preceding paragraph. Decide whether '
        'the new point continues, qualifies or contrasts with the earlier one. State that relationship '
        'in the opening, using the ideas themselves to form the connection. A transition is most useful '
        'when it explains the move in the argument, rather than simply announcing that another point is coming.'),
    'topic_vague_focus': (
        'The opening at {anchor} is the place to make this paragraph’s task explicit. Name the '
        'particular issue behind the general wording, then explain the point the paragraph will make '
        'about it. Read the following evidence and explanation against that opening. If they develop '
        'a more specific idea, use that idea to guide the revision instead of adding a broad introductory statement.'),
    'comparison_topic_general': (
        'For the paragraph beginning {anchor}, decide what the comparison helps readers see about '
        'the two works. Identify the feature you will examine in each, then explain the relationship '
        'between them in the opening sentence. The supporting examples can then develop that relationship, '
        'giving the paragraph a purpose beyond naming a theme that both works share.'),
    'comparison_topic_focus': (
        'The opening at {anchor} introduces another shared idea in the works. Decide which feature '
        'of each work the paragraph will compare and what the comparison reveals about that idea. '
        'State that relationship before discussing the examples. This will help readers understand '
        'why the two examples belong together, rather than treating them as separate illustrations of a general theme.'),
    'topic_evidence_opener': (
        'Look at {anchor} and identify the point you want the evidence to help establish. Give '
        'readers that point in your own words before introducing the source or result. Then explain '
        'the connection after presenting the evidence. This order lets the paragraph’s reasoning '
        'guide the use of the source, instead of asking the source to introduce the paragraph’s purpose.'),
    'annotation_relevance_brief': (
        'Expand the research-use discussion at {anchor}. Specify which finding or argument you '
        'expect to use, which part of your research question it addresses and how you will use it '
        'in the paper. Keep this explanation distinct from a summary of the source. If the connection '
        'is indirect, describe that limit so the annotation accurately represents what the source can contribute.'),
    'annotation_parts_combined': (
        'In the annotation containing {anchor}, distinguish the jobs performed by the summary, '
        'evaluation and explanation of research use. The summary reports the source’s main point; '
        'the evaluation considers its reliability; the final part explains its place in your project. '
        'If your assignment asks for separate parts, make those changes of purpose visible through '
        'paragraph breaks, while keeping all three attached to the same source entry.'),
    'assessment_interpretation': (
        'For the results at {anchor}, explain what the reported measures contribute to the discussion. '
        'Connect each interpretation to the assessment result and observation that support it, and '
        'distinguish those observations from possible explanations. The reader needs to understand '
        'why the results matter in this report, without the prose implying more certainty or a broader conclusion than the evidence permits.'),
    'informal_diction': (
        'Reconsider the wording at {anchor} in its full sentence. Identify the particular idea, '
        'effect or action you mean, then choose wording that states it directly. Check other uses '
        'of the same expression after revising this example. The aim is to make the meaning easier '
        'to follow while keeping your intended point and the level of formality the assignment requires.'),
    'para_passive': (
        'Read the sentence containing {anchor} with attention to who performs the action. Where '
        'that person or group matters to the explanation, name them and make the action explicit. '
        'Keep a passive construction when the action or result is the appropriate focus. Apply the '
        'same judgment to the other marked examples, rather than changing every passive form automatically.'),
}
