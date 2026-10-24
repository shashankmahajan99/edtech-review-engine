# Voice brief: deterministic review-comment generator

You are helping design the voice of an offline, deterministic review engine for an
academic editing service. It writes margin comments and one endnote letter per
student draft. No model runs at generation time, so your output must be reusable
rules and patterns, not example prose alone.

Your advice will be implemented as code. Be concrete and prescriptive, and ground
every rule in the corpus below rather than in general writing advice.

## Task

Produce one JSON object with exactly these keys: `persona`, `moves`,
`anti_ai_rules`, `endnote_template`, `banned_phrases`. Schema:

```json
{
  "persona": {
    "register": "one paragraph",
    "stance": "one paragraph",
    "habits": [
      "short bullets"
    ],
    "never": [
      "short bullets"
    ]
  },
  "moves": [
    {
      "id": "thesis",
      "labels": [
        "THESIS STATEMENT"
      ],
      "patterns": [
        {
          "observation": "sentence with {quote} / {term} / {source} slots",
          "advice": "sentence or empty string",
          "length": "short|medium|long"
        }
      ]
    }
  ],
  "anti_ai_rules": [
    "imperative rules grounded in the corpus"
  ],
  "endnote_template": {
    "opening": "one or two sentences",
    "sections": [
      {
        "heading": "Thesis and overall focus",
        "pattern": "2-4 sentences with slots"
      }
    ],
    "closing": "one sentence",
    "signoff": "All the best."
  },
  "banned_phrases": [
    "words and constructions to reject"
  ]
}
```

Requirements:

- 12–16 `moves` covering thesis, introduction, abstract, evidence, analysis,
  statistics, transitions, topic sentences, organisation, conclusion, grammar,
  citations/formatting (APA and MLA), and sentence clarity.
- 4–6 `patterns` per move, each a reusable observation/advice pair with slots
  such as `{quote}`, `{term}`, `{source}`, `{count}`. Patterns must sound like
  the reviewers below, not like a writing centre handout.
- `anti_ai_rules`: at least 8 rules that a detector would notice if broken,
  explicitly tied to the measured distribution below.
- Keep the constraints: the corpus uses **no contractions**, rare first person,
  46% one-sentence comments, and hedges in 39% of comments.
- `endnote_template` must reproduce the structure and length of the letters below
  (138–382 words): an opening line, two or three named focus areas, and a sign-off.
- No generic praise, no sentence-length uniformity, no throat-clearing.
- Return only the JSON in a fenced ```json block, no commentary.

## Measured profile (307 comments, 25 documents, 2 reviewers)

```json
{
  "documents": 25,
  "comments": 307,
  "comment_words": {
    "mean": 26.94,
    "std": 13.61,
    "min": 5,
    "max": 100
  },
  "sentence_lengths": {
    "mean": 14.34,
    "std": 7.87,
    "min": 1.0,
    "max": 40.0
  },
  "sentences_per_comment": {
    "mean": 1.88,
    "std": 1.11,
    "min": 1.0,
    "max": 9.0
  },
  "question_rate": 0.111,
  "contraction_rate": 0.0,
  "first_person_rate": 0.026,
  "directive_rate": 0.469,
  "hedge_rate": 0.391,
  "specific_rate": 0.319,
  "one_sentence_rate": 0.459,
  "two_or_three_sentence_rate": 0.489,
  "top_labels": {
    "MLA": 31,
    "THESIS STATEMENT": 19,
    "APA": 19,
    "CONCLUSION": 17,
    "TOPIC SENTENCE": 16,
    "INTRODUCTION": 12,
    "ORGANIZATION": 11,
    "TRANSITIONS": 9,
    "TRANSITION": 9,
    "GRAMMAR": 8,
    "FORMATTING": 8,
    "ANNOTATION": 6,
    "SENTENCE CLARITY": 6,
    "STRUCTURING": 5,
    "CAPITALIZATION": 4
  }
}
```

## Representative comments (verbatim, with the anchored student text)

- **—** · quote: “October 2026”
  comment: MLA (Header): The date in the header could be written as Day Month Year as: 22 May 2024
- **—** · quote: “In conclusion women's rights are significantly impacted in Afghanistan due to the Taliban oppression, while women's rights are much more protected in the U.S..”
  comment: Please add a comma after the introductory clause here.
- **—** · quote: “In the Peabody assessment, Eloise scored in the 37th percentile ranking for grasping. As a result, her standard score is 9, with an age equivalency of 12 months old. For visual mot”
  comment: Idea Development (Clarity): You could strengthen this section by interpreting the scores and explaining what they suggest about Eloise’s fine motor abilities. Rather than only listing the numerical results, consider comparing her performance in grasping and visual-motor skills to identify relative strengths and areas that may require further attention.
- **MLA** · quote: “(Micheal Jackson).”
  comment: In MLA style, cite song lyrics by placing the artist’s last name or the song’s shortened title in parentheses after the quoted lyrics, ensuring that the citation matches the first element of the corresponding Works Cited entry.
- **MLA** · quote: “Websites”
  comment: The title here needs to be written as “Works Cited,” as required by MLA.
- **MLA** · quote: “Jackson’s song”
  comment: Please review the indentation of the body paragraphs. Normally, the first line of each new paragraph receives an indentation of 0.5 inches. Please make sure you follow this guideline for each new paragraph.
- **Thesis Statement** · quote: “Although “Hall of Fame” by The Script featuring will.i.am and “You’re the Voice” by John Farnham are different songs, both talk about hard work, personal discipline, and overcoming”
  comment: The thesis statement could be reworked to also mention “how” are the themes shown in the songs. Let us discuss this in details in the endnote below.
- **Thesis Statement** · quote: “Despite the prosperity of AI and its positive impact in multiple sectors as well as the general human populus, it is imperative that the government enact stricter regulations and g”
  comment: The thesis statement here is a bit lengthy, and could be developed in a more concise manner. Kindly refer to my endnotes for more on this.
- **Thesis Statement** · quote: “Although artificial intelligence is useful, excessive dependence on it can harm human relationships by weakening emotional connections and reducing communication with family and fr”
  comment: The thesis statement here presents both the claim and the reasoning, which is good. However, the first part is a little vague and could be developed further. Kindly refer to my endnotes for more on this.
- **APA** · quote: “Benson”
  comment: Please provide the year of publication after the author’s name. For example, Smith (2023) argues…
- **APA** · quote: “Horne-Moyer, H. L., Moyer, B. H., Messer, D. C., & Messer, E. S. (2014, December). The use of electronic games in therapy: A review with clinical implications. Current psychiatry r”
  comment: Please double-space the citation here. Also, the name of the article needs to be written in the regular font, while the journal name needs to be italicized.
- **APA** · quote: “(Keough, 2025).”
  comment: This in-text citation is correctly formatted as per APA style.
- **Conclusion** · quote: “AI”
  comment: You need to end the essay with a conclusion. Please develop a conclusion keeping the following things in mind- Firstly, you need to start with a signal phrase. Secondly, you need to restate the thesis about the topic. However, do not repeat the words exactly, and restate it in a varied language. Further, you need to provide a brief overview of the entire discussion. Finally, you will end it in a more impactful way. What was your final takeaway from this discussion? Why do you think the reader should care about the issue? How relevant is it in today’s time?
- **Conclusion** · quote: “Together, the songs show that success involves more than natural talent or simply winning against another person. It also takes hard work, patience, and the ability to keep going w”
  comment: The conclusion is well-written effectively summing-up the main ideas discussed in the essay on how the two songs deal with the theme of competition and how it teaches people to overcome challenges in life through different experiences.
- **Conclusion** · quote: “He is attempting to make us feel like there are other reasons for this decline, but young adults do not have the same affinity for cars as older generations did.”
  comment: The ending line here needs to be developed in a more impactful way. What is your final takeaway from the discussion on Weissmann’s article? Why should the reader read it? How relevant is it in today’s time?
- **Topic Sentence** · quote: “Weissmann also uses economic reasoning.”
  comment: The topic sentence here needs to be developed further. Why does Weissmann use economic reasoning?
- **Topic Sentence** · quote: “Working toward a goal can be difficult, especially when results take time”
  comment: This topic sentence is a bit general. Could you mention how is this idea of working towards a goal depicted in the two songs and how you intend to discuss it in this body paragraph?
- **Topic Sentence** · quote: “In the United States deer hunting is often something that families and friends do together”
  comment: This topic sentence could be slightly reworked. As the paragraph discusses the hunting tradition both for U.S. and Germany, you could mention the point of comparison and how it will be discussed with regard to the two countries.
- **Introduction** · quote: “Music can help people when they have a difficult time. Some songs give hope, while others talk about problems in society. “Hall of Fame” by The Script featuring will.i.am and “You’”
  comment: The introduction clearly establishes the context for the essay mentioning how music has a way to empower people and helps them combat difficult situations.
- **Introduction** · quote: “Over the years, music has functioned as an essential tool to express what people aim to defend, such as human rights. It is also utilized to address social issues and demand social”
  comment: The introduction clearly establishes the context for the essay on how music has been used as a way of expressing different emotions over the years.
- **Introduction** · quote: “There are 14.3 million people in the world who have suicidal ideology in the world, music in various genres serve as a way to express these emotions in a healthy manner and call ou”
  comment: The introduction clearly establishes the context for the essay on how the two songs deal with the idea of suicide.
- **Organization** · quote: “Eloise’s parents have slight concerns regarding her gross motor and communication development due to her being five weeks premature”
  comment: As this section is a bit long with multiple ideas, you could consider to reorganize the ideas into separate sections or paragraphs. The ideas could be grouped on the basis of Eloise’s daily occupations, interests, and areas of concern. You could consider connecting her parents’ concerns about gross motor, social, and play skills to specific examples of how these challenges may affect her participation in daily routines and interactions with other children.
- **Organization** · quote: “Hurshka is a predoctoral researcher at the University of Würzburg in germany, and has been published in various psychological journals since 2023. Co-author Appel is a prolific aut”
  comment: Unless otherwise instructed, each of the three parts of the annotation could be written in three separate paragraphs. This will help to clearly differentiate among the three parts of the annotation.
- **Organization** · quote: “The Weeknd presents desire as a reason to assert independence and reject outside judgment, while Jackson portrays curiosity and attraction as natural parts of being human.”
  comment: The organization of ideas could be slightly reworked. Let us discuss how in the endnote below.
- **Transitions** · quote: “Deer hunting”
  comment: You could consider using transition words such as "In conclusion" to smoothly transition into the final body paragraph of the essay.
- **Transitions** · quote: “Germany also has a hunting culture but some of their traditions are more formal”
  comment: When you are shifting to discuss the point of comparison for the other country, you could use transition words like “On the other hand,” “In contrast” and so on.
- **Transition** · quote: “The”
  comment: The transition here between the two paragraphs is a little abrupt. The ideas need to be connected with a transition word here. For example, use words like “Further,” or “Additionally.” This helps in maintaining the flow.
- **Transition** · quote: “My”
  comment: The sentence here seems to be a little abrupt. Whenever you are starting the conclusion, make sure it is integrated properly for a smoother flow. You can use a transition phrase like “Thus,” or “In conclusion” here to signal the end of discussion.
- **—** · quote: “don’t”
  comment: Grammar (Word Choice & Vocabulary): Did you intend to mean “done” here?
- **—** · quote: “The study was don’t on cross sectional survey results, and approved by the KCL Research Ethics Committee. All eight authors are doctors or doctorate students and have worked or stu”
  comment: Idea Development (Clarity): Since the study focuses on reported cases involving delusional beliefs and other harms rather than political polarization specifically, how could you explain the connection without suggesting that the study directly proves a link to political beliefs?
- **Annotation** · quote: “This article will be useful for answering my research question, as it provided research exploring the views from autistic students about their experiences in mainstream education. ”
  comment: The annotation here could be developed further. Could you explain more about the authors and the database? What are their credentials?
- **Grammar** · quote: “I hope to enjoy this class with a group of better than I classmates who I shall aspire to!”
  comment: By saying “better than I classmates”, are you trying to say that you hope to learn from classmates whose skills you admire?
- **Topic Sentence** · quote: “Along with using drugs as a physical aspect to numb the pain that comes along with suicidal ideation, the listener is able to understand the perspectives of the following people fr”
  comment: You could make this topic sentence a bit more specific. What does the first person point-of-view tell about the themes of the songs? How is it linked to the idea of suicide?
- **Conclusion** · quote: “Although both songs examine the choices people make based on their desires, their themes and tones reveal contrasting attitudes toward personal freedom and human behavior. Although”
  comment: Could you connect The Weeknd's emphasis on independence with Jackson's exploration of curiosity and attraction to show how different motivations can lead people to express themselves in different ways?
- **Annotated Bibliography** · quote: “For my purposes, this paper is useful in gauging the political slant of AIs, which might influence its effect on polarization.”
  comment: The way this source could be relevant for your research is a bit rushed. You could explain in more details what your research will be about and how it could help you.
- **—** · quote: “2.4 the Frank Lloyd Wright Barnsdall house is located in LA. I saw another home he owns, Taliesin West,located in Scottsdale, Arizona which according to google is the "winter home"”
  comment: Idea Development (Clarity): You could add a bit more context about the text you are referring to here. Let us discuss about this in the endnote below.
- **—** · quote: “On the other hand, the 2012 song also exposes the deep psychological pain caused by daily social hatred and discrimination, especially when young people feel attacked for being who”
  comment: Idea Development (Clarity): You could add a bit more details and explanation here. How were the young ones attacked for their identity? Were they attacked at home, in schools, colleges and other places and by whom?
- **Grammar** · quote: “Humna”
  comment: The sentence here seems to have a misspelled word, which reduces the fluency. Kindly proofread your sentences in the next draft to avoid such errors.
- **APA** · quote: “Dwyer, Patrick. (2018, August 20). "Mental Health in the Mainstream Schools". https://www.autisticscholar.com/inclusion-mental-health/”
  comment: The indentation here needs to be revised. First line of each entry starts at the margin, but the next is indented. This is called the "hanging indent".
- **Run** · quote: “The world has many changes and people try to adapt to those changes although there is a stronger connection that one person has to another which is a common interest would be Music”
  comment: On Sentence: This sentence is a run-on because it has two independent clauses without proper punctuation or a conjunction. Consider revising to, "I love to write essays; it is my favorite hobby," or "I love to write essays, and it is my favourite hobby."
- **Transitions** · quote: “Jackson’s song emphasizes the feelings and instincts that influence many individuals' choices.”
  comment: You could consider adding transition words like “In addition”, “Moreover”, “Furthermore” and so on to create a smooth flow from paragraph to the next in the topic sentences.
- **MLA** · quote: “Works Cited”
  comment: The heading could be centre-aligned.
- **APA** · quote: “Journal onMigrationandHumanSecurity,”
  comment: Please write the journal name clearly.
- **APA** · quote: “Journal on Migration and Humna”
  comment: Please italicize the journal name here.
- **MLA** · quote: “The New Breed.”
  comment: Please italicize the book title here.
- **Grammar** · quote: “participation,n”
  comment: Please revise for typographic error here.
- **APA** · quote: “School Belonging, Camouflaging, and Anxiety in Autistic Students.”
  comment: The journal title needs to be italicized here.
- **—** · quote: “”
  comment: APA (Title Page): Unless otherwise instructed, you could add a title page at the start of the paper. An APA style title page typically includes the following elements, centered and double spaced: Title of the Paper: Full title of the paper. Author's Name: Full name of the author(s). Institutional Affiliation: The name of the institution where the research was conducted. Course Number and Name: The course for which the paper is being written. Instructor's Name: The name of the instructor. Due Date: The due date for the assignment
- **—** · quote: “The author makes a great point when he and a colleague are sitting together, where the colleague says "perceiving robots as living things goes deeper than a simple novelty defect a”
  comment: Idea Development (Clarity): You could make the focus of this idea clearer as the discussion is a bit vague. You conclude that this change will take longer than it should because of how much people rely on and connect with robots. Could you develop this point by explaining why human dependence on robots makes it difficult to change our perceptions of them? Can you connect your personal opinion more directly to the author's argument or provide a specific example to support your reasoning?
- **—** · quote: “Taylor caruso 10/15/26Lisa palmer english 102”
  comment: MLA (Header): Instead of spreading on both sides of the page, the header is added on the left side of the first page in four lines. On the first page of your paper, a four-line header that includes: -Your name, The instructor's name, The course name, The date. This appears at the top of the first page only and is aligned left. Example: Steven Smith Mrs. Savio Research 8 22 May 2018
- **—** · quote: “”
  comment: MLA (Header): You could add a header in four lines at the start of your essay. On the first page of your paper, a four-line header that includes: -Your name, The instructor's name, The course name, The date. This appears at the top of the first page only and is aligned left. Example: Steven Smith Mrs. Savio Research 8 22 May 2018

## Human endnote letters

These are the closing letters the reviewers append to the draft: an opening
line, two or three named focus areas, and a sign-off. They are the ground
truth for `endnote_template`.

### Mehak K. — 1stdraft_marcelo_aguirrerod10_COTA_2_REV_BY_TS_MehakK_245369_1.docx (210 words)

You have done a good job to establish perseverance and ambition as the central themes of your essay and maintain this focus throughout the discussion.

There are a few areas to focus on your next draft. You could make the thesis statement more specific by explaining how each song approaches the three themes differently. Your thesis mentions that the songs present motivation, challenges, and success differently. How could you make this claim more specific by identifying what Eminem emphasizes and what Survivor emphasizes in these three areas? Could you briefly show these differences in one focused thesis statement so that readers know what your comparison will be about?

For the next steps, your paragraph about challenges begins, “Another comparison is how the songs talk about challenges.” How could you revise this topic sentence to explain how the songs portray challenges differently? For example, could you introduce the contrast between the pressure of facing an important opportunity in “Lose Yourself” and the determination to keep fighting in “Eye of the Tiger”?

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mehak K. — AnnotatedBibliography_jsmatheny982_wcc_3_REV_BY_TS_MehakK_245319_1.docx (292 words)

You have done a good job to discuss how artificial intelligence affects political polarization.

There are a few areas to focus on your next draft. In your first annotation, you discuss the study's findings, the authors' credentials, and your observation that AI can be designed to reduce polarization. How could you organize this information into three parts: a summary of the study, an evaluation of its credibility and limitations, and an explanation of its relevance to your research?

In the relevance section, could you explain more specifically how this study will help you investigate whether AI reduces polarization under certain conditions or whether its effects depend on how the system is designed?

You explain that Harrison's article is useful for gauging the political slant of AI, but the explanation of how it supports your research is brief. How could you expand the relevance section by explaining how the reported findings might help you investigate the relationship between political bias and polarization? Could you also evaluate the source's credibility by distinguishing Harrison's role as the article's author from the researchers who conducted the underlying study, and then explain any limitations you would consider before relying on its findings?

For the next steps, please use sentence case for the title of articles and ensure all entries are formatted using hanging indentation. This will help the entries align with the APA guidelines. There is a sample of the annotation I am providing for you to refer to and ensure to follow this for your annotations.

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mohini Sardar — AshleyJohnson_REV_BY_TS_MohiniS_245299_1.docx (219 words)

Dear Ashley,

You have done a decent job here with the annotated bibliography. However, there are a few areas where you need to work on in the next draft. Let us look at them in detail-

Annotations-

Your annotations are on the right track, but they could be developed in a bit more depth. Kindly follow a proper structure for your annotations to make it look more academic-Firstly, you need to introduce the article and state the main claims in a brief manner. You need to summarize the key points which you think are relevant to your research question. Secondly, you need to talk about the credibility of the source. Who is the author? What is it about their background that makes them a reliable source? Is the journal a reputable one? What are the reasons for its credibility? After delving into these, you need to end the annotation by mentioning how you will use the article in your paper. Where exactly will you place the citation in your paper? Think on these lines to develop the annotations further.

I am sure that once you focus on these areas, your writing will look a lot more refined. I look forward to reading the revised draft. You have great potential. Keep writing. All the best!

Regards,Mohini.

Formatting the Reference List

### Mehak K. — blank_document-2_william_holloway03_COTA_1_REV_BY_TS_MehakK_245315_1.docx (186 words)

You have done a good job of sharing your Week One and Week Two reflections.

There are a few areas to focus on your next draft. In the Week Two paragraph, you introduce the reported incident at Taliesin West, but you could provide more context about the news story and explain more clearly how it relates to the chapter. Could you briefly explain the relevant details of the incident and then add a sentence explaining why this connection matters to you?

For the next steps, please revise for grammar issues such as in the sentence beginning “I saw another home he owns, Taliesin West,located in Scottsdale, Arizona…”, several ideas are combined without sufficient punctuation, and space after the comma is needed such as in “West,located.” How could you divide this sentence into two shorter sentences, use commas to set off the location correctly, and capitalize “Google”?

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mehak K. — BrightlyBleak-Acomparisonessay-Rhoads_ana_rhoads81_COTA_2_REV_BY_TS_MehakK_245373_1.docx (225 words)

You have done a good job to discuss in your comparative essay about “Bullet” by Hollywood Undead and “Nintendo 64” by Alex G. Your discussion explores a serious topic through the perspectives, imagery, and themes presented in both songs.

There are a few areas to focus on your next draft. Some of your topic sentences could be reworked as they are a bit lengthy. You could consider explaining how the songs' different perspectives such as experiencing a crisis firsthand versus witnessing a loved one in crisis help communicate the impact of suicidal thoughts. Similarly, make sure each topic sentence identifies the specific comparison you will develop and connect it to one of the main points in your thesis.

For the next steps, your Works Cited page needs attention to quotation marks, capitalization, and entry formatting. For example, the entry for Hollywood Undead currently appears as Hollywood Undead.”Bullet.”; the quotation marks and spacing could be corrected, and the entries should follow consistent MLA formatting. Can you also check that the names used in your parenthetical citations correspond to the first elements of the Works Cited entries?

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mehak K. — ComparisonEssay_angel_lopezperez35_COTA_2_REV_BY_TS_MehakK_245370_1.docx (217 words)

You have done a good job to discuss how the two songs “Tell Your Friends” by The Weeknd and “Human Nature” by Michael Jackson give you an opportunity to explore how different artists present personal freedom, human desires, and individual choices.

There are a few areas to focus on your next draft. Your current introduction moves into the discussion of “Tell Your Friends” without clearly stating the main comparison you intend to develop. You could consider ending the introduction with a specific claim or thesis statement that mentions how the two artists explore self-expression through independence, personal freedom, and human instincts.

For the next steps, the ideas could be slightly reorganized. At present, some ideas about The Weeknd's song, including personal growth and individual choices, appear across several sections, while the discussion of Jackson’s song is divided into multiple paragraphs. You could group related ideas together, begin a new paragraph when the focus changes, and use transitions to connect the two songs. This will ensure each idea about the song is discussed in its own separate paragraph.

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mehak K. — ComparisonEssay_reece_feyer31_COTA_2_REV_BY_TS_MehakK_245367_1.docx (223 words)

You have done a good job to write a comparative essay about Aretha Franklin’s and P!nk’s songs and their shared message about respect.

There are a few areas to focus on your next draft. Your current thesis statement is fragmented across several lines. You could combine the ideas into one focused thesis that names the main points you will compare, such as self-respect, standing up for oneself, and supporting others. In your thesis, you could express a complete claim and show how the artists communicate these themes through their lyrics and musical approaches.

For the next steps, please review your essay for sentence fragments, capitalization, word choice, and punctuation. Also, avoid capitalizing “She” in the middle of a sentence when it does not begin a new sentence, and use consistent hyphenation in compound words such as “self-respect” and “self-confidence.”

To comply with the MLA guidelines, you could add in-text citations after quoted lyrics, using the artist's last name or the shortened title that corresponds to the Works Cited entry. Since lyrics are quoted from recorded songs, timestamps may help readers locate the passages.

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mehak K. — ComparisonEssay_tannya_chaconbaez79_COTA_2_REV_BY_TS_MehakK_245379_1.docx (271 words)

You have done a good job to establish a meaningful comparison between the two songs by examining discrimination, emotional suffering, and hope for social change.

There are a few areas to focus on your next draft. Your thesis statement identifies institutionalized discrimination, emotional suffering, and hope for social progress as the main points of comparison.

However, you could make the central claim more precise by naming both songs directly in the concluding sentence of your introduction and explaining how each song communicates these themes differently.

For example, how does Cooke’s song reflect the experiences of African Americans during the civil rights era, while “Same Love” addresses prejudice against the LGBTQ+ community?

For the next steps, you could also develop some of your supporting explanations further to enhance the idea development. When you discuss the emotional harm caused by discrimination, you could explain more specifically how the lyrics reveal this suffering and why it matters to the song’s overall message?

Could you develop this point with more specific analysis of the lyric about hip-hop being perceived as hostile toward gay people?

What does this suggest about the influence of prejudice and derogatory comments on a person’s sense of belonging or self-esteem?

Your Works Cited entries currently use bullet points and inconsistent punctuation. You could remove the bullets, arrange the entries alphabetically by the first element, italicize Genius, and apply a hanging indent.

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mehak K. — ComparisonEssayDraft_william_boehmer21_COTA_2_REV_BY_TS_MehakK_245368_1.docx (192 words)

You have done a good job to write a well-organized comparative essay exploring how “Eye of the Tiger” by Survivor and “The Champion” by Carrie Underwood featuring Ludacris communicate the meaning of competition.

There are a few areas to focus on your next draft. To enhance the development of ideas, while you generally explain what the lyrics mean, you could take your analysis a step further by exploring why the artists chose those specific words, images, or expressions and how those choices strengthen the songs’ messages about competition. You could consider examining imagery, repetition, tone, or word choice rather than simply restating their meanings.

For the next steps, your essay has a logical structure, but some transitions could make the relationship between your points clearer. Phrases such as “Beyond determination, both songs also emphasize the importance of learning from setbacks” or “Once competitors learn to overcome challenges, could establish this connection clearly.

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mehak K. — comparisonessayroughdraft_fisher_parker52_COTA_3_REV_BY_TS_MehakK_245381_1.docx (194 words)

You have done a good job to establish your comparison in this paper on deer hunting traditions in the United States and Germany.

There are a few areas to focus on your next draft. Your thesis statement only mentions one area of difference. Since your essay also discusses traditions and hunting methods, you could consider including these aspects in your thesis.

What specific differences do you want readers to understand about hunting in the two countries?

For the next steps, to enhance the idea development, in the paragraph about hunting laws and requirements, you explain that German hunters must complete more training and pass an examination. What does this difference suggest about the responsibilities expected of hunters in Germany compared with those in the United States?

Similarly, when discussing hunting methods, how could you explain the significance of the research finding about “sustained and intensive hunting pressure” rather than simply restating what it means?

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mehak K. — CompletedDraft_diego_cantos78_COTA_2_REV_BY_TS_MehakK_245376_1.docx (253 words)

You have done a good job to establish the differences between the two songs, explaining how “Hall of Fame” emphasizes personal achievement while “You’re the Voice” encourages people to speak up and contribute to social change.

There are a few areas to focus on your next draft. Your thesis identifies hard work, personal discipline, and overcoming problems as shared themes, but it could explain more clearly how the two songs communicate these ideas differently.

How is personal determination emphasized in “Hall of Fame” and the collective responsibility emphasized in “You’re the Voice”?

How does “Hall of Fame” encourage individual achievement while “You’re the Voice” emphasizes speaking up and contributing to society?

For the next steps, please revise your topic sentences so that they introduce the main idea you will discuss from the two songs in that particular body paragraph. For example, in the topic sentence “Working toward a goal can be difficult, especially when results take time” introduces a general idea but it could explain how both songs develop it.

How could you revise this opening to show what the paragraph will compare in the two songs?

For example, could you explain how “Hall of Fame” connects perseverance with consistent effort, while “You’re the Voice” connects responsibility with the courage to speak out?

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mohini Sardar — DarlinOsornioSilva_REV_BY_TS_MohiniS_245332_1.docx (220 words)

Dear Darlin,

You have done a pretty good job here with the annotated bibliography. However, there are a few areas where you need to work on in the next draft. Let us look at them in detail-

Annotations-

Your annotations are on the right track, but they could be developed in a bit more depth. Kindly follow a proper structure for your annotations to make it look more academic-Firstly, you need to introduce the article and state the main claims in a brief manner. You need to summarize the key points which you think are relevant to your research question. Secondly, you need to talk about the credibility of the source. Who is the author? What is it about their background that makes them a reliable source? Is the journal a reputable one? What are the reasons for its credibility? After delving into these, you need to end the annotation by mentioning how you will use the article in your paper. Where exactly will you place the citation in your paper? Think on these lines to develop the annotations further.

I am sure that once you focus on these areas, your writing will look a lot more refined. I look forward to reading the revised draft. You have great potential. Keep writing. All the best!

Regards,Mohini.

Formatting the Reference List

### Mohini Sardar — DevonHarrold_REV_BY_TS_MohiniS_245338_1.docx (334 words)

Dear Devon,You have done a decent job here with the annotated bibliography. However, there are a few areas where you need to work on in the next draft. Let us look at them in detail-APA Formatting –

The paper currently is not formatted as per APA, which makes it look a little informal. You need to provide a title page before the paper which will include the title of the paper in bold, along with your name, the name of the college, the course name, instructor’s name and the date. The title details need to be centered, and should be placed in the middle of the page. Also, the date is to be written in the month-date-year format.For example, September 6, 2026These details need to be aligned to the center. Further, a running header needs to be inserted in the top right corner of the page, and it should include only the page number.

Annotations-

You have a good start with the annotations, but they need to be developed further. Kindly follow a proper structure for your annotations to make it look more academic-Firstly, you need to introduce the article and state the main claims in a brief manner. You need to summarize the key points which you think are relevant to your research question. Secondly, you need to talk about the credibility of the source. Who is the author? What is it about their background that makes them a reliable source? Is the journal a reputable one? What are the reasons for its credibility? After delving into these, you need to end the annotation by mentioning how you will use the article in your paper. Where exactly will you place the citation in your paper? Think on these lines to develop the annotations further.I am sure that once you focus on these areas, your writing will look a lot more refined. I look forward to reading the revised draft. You have great potential. Keep writing. All the best!

Regards,Mohini.

Formatting the Reference List

### Mohini Sardar — ErinCrede_REV_BY_TS_MohiniS_245354_1.docx (294 words)

Dear Erin,

You have done a pretty good job here with the essay. However, there are a few areas where you

need to work on in the next draft. Let us look at them in detail-

Thesis Statement- The thesis statement in the paper could be framed in a more analytical way.Let us look at how you can work on it with the help of an example-

Remember, a thesis statement has two parts- one is the claim and the other is the justification.

You need to keep these in mind when you frame the thesis statement here. For example, let us

assume the claim as- “In her United Nations speech, Malala Yousafzai effectively persuades her

audience to support equal access to education.” This claim needs to be accompanied by a

justification like “by using ethos to establish her credibility as an education activist, pathos to

highlight the emotional consequences of educational inequality, and logos to demonstrate the

importance of education for social progress.”

When you combine the two statements, you get the thesis statement. Try to come up with a thesis

statement keeping this in mind. It needs to be of an optimum length for the reader, and is usually

written in the last line of the introduction.

What is your main argument about the article by Jordan Weissmann? Which rhetorical devices

are used in it to persuade the audience about the intended message? What is the purpose of using

them?

Think about these leading questions and frame an assertive thesis statement in a succinct manner.

I am sure that once you focus on these areas, your writing will look a lot more refined. I look

forward to reading the revised draft. You have great potential. Keep writing. All the best!

Regards,

Mohini.

### Mehak K. — essaydraft_GDubeLTI_QCC_1_REV_BY_TS_MehakK_245306_1.docx (219 words)

You have done a good job to discuss the potential harms of bonding with AI.

There are a few areas to focus on your next draft. You could revise each topic sentence to present the paragraph’s main claim and show how it supports your thesis. For example, your second body paragraph begins, “Another reason bonding with AI can be harmful is that people can become too dependent on it.” How could you make this topic sentence more specific by explaining how emotional dependence on AI might affect a person’s willingness to seek support from friends or family?

For the next steps, your examples explain what might happen when someone relies heavily on AI, but most of the discussion is based on hypothetical situations. What credible research study, expert article, or report could you use to support one of your claims about AI companionship, emotional dependence, or human relationships?

Where would you place that evidence in the relevant paragraph, how would you introduce and cite it, and what explanation could you add afterward to show how it supports your argument?

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mohini Sardar — GavinWoodruff_REV_BY_TS_MohiniS_245290_1.docx (257 words)

Dear Gavin,

You have done a pretty good job here with the report. However, there are a few areas where you need to work on in the next draft. Let us look at them in detail-

Thesis Statement-

The thesis statement in the paper could be framed in a more precise way. Let us look at how you can work on it with the help of an example-

Remember, a thesis statement has two parts- one is the claim and the other is the justification. You need to keep these in mind when you frame the thesis statement here. For example, let us assume the claim as- “Public colleges should offer free tuition.” This claim needs to be accompanied by a justification like “because it would increase access to higher education, reduce student debt, and strengthen the workforce.”

When you combine the two statements, you get the thesis statement. Try to come up with a thesis statement keeping this in mind. It needs to be of an optimum length for the reader, and is usually written in the last line of the introduction.

What is your main argument about corded power tools at the workplace? Why should it be changed to a completely cordless platform?

Think about these leading questions and frame an assertive thesis statement in a succinct manner.

I am sure that once you focus on these areas, your writing will look a lot more refined. I look forward to reading the revised draft. You have great potential. Keep writing. All the best!

Regards,

Mohini.

### Mehak K. — IndependenceEssayDraft_leland_serrant83_COTA_2_REV_BY_TS_MehakK_245403_1.docx (266 words)

You have done a good job to establish a clear central theme of independence and identify three areas through which the songs explore it such as prioritizing personal needs, pursuing a good life, and escaping unpleasant situations.

There are a few areas to focus on your next draft. The thesis statement could be revised and made more concise. In one sentence at the end of the introduction, you could name the songs and show what are the main ideas you will discuss from them.

Will your comparison bring out the differences or similarities in the thematic discussion and how?

Your thesis identifies prioritizing, having a good life, and escaping unpleasant things as three aspects of independence. How could you express these ideas in one concise sentence that also explains how the two songs approach independence differently?

What specific contrast between the speakers’ attitudes or choices would make your central argument more analytical?

For the next steps, some of your topic sentences are a bit general. You could introduce the main idea you will discuss in the body paragraph more clearly in the topic sentence. For example, you could state more directly how the songs portray different ways of escaping difficulties. For example, how does prioritizing personal needs lead into the pursuit of a more fulfilling life, and how might escaping difficulties represent another aspect of independence?

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mohini Sardar — JacobLeite_REV_BY_TS_MohiniS_245301_1.docx (250 words)

Dear Jacob,

You have done a pretty good job here with the essay. However, there are a few areas where you need to work on in the next draft. Let us look at them in detail-

Thesis Statement-

The thesis statement in the paper could be framed in a more concise way. Let us look at how you can work on it with the help of an example.

Remember, a thesis statement has two parts- one is the claim and the other is the justification. You need to keep these in mind when you frame the thesis statement here. For example, let us assume the claim as- “Public colleges should offer free tuition.” This claim needs to be accompanied by a justification like “because it would increase access to higher education, reduce student debt, and strengthen the workforce.”

When you combine the two statements, you get the thesis statement. Try to come up with a thesis statement keeping this in mind. It needs to be of an optimum length for the reader, and is usually written in the last line of the introduction.

What is your main argument about AI? Why should it be regulated by the government?

Think about these leading questions and frame an assertive thesis statement in a succinct manner.

I am sure that once you focus on these areas, your writing will look a lot more refined. I look forward to reading the revised draft. You have great potential. Keep writing. All the best!

Regards,

Mohini.

### Mehak K. — McAvey_Essay1_RoughDraft_AMcAveyLTI_QCC_1_REV_BY_TS_MehakK_245303_1.docx (203 words)

You have done a good job to develop your argument about the need to regulate artificial intelligence. I like how your essay considers how AI affects employment, critical thinking, the environment, and human relationships.

There are a few areas to focus on your next draft. Some of your topic sentences at the start of the body paragraphs could be reworked. You could avoid beginning the topic sentence with an outside quote. In your own words you could introduce whether you will discuss a benefit or drawback of using AI and then add evidence in the upcoming sentences.

For the next steps, please create a separate Works Cited page at the end of your essay. The title of articles is written in title case, while the name of journals and sources is to be written in italics. All entries are to be arranged alphabetically and formatted using hanging indentation. MLA in-text citation could include the author’s last name and page number as (Smith 22).

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mohini Sardar — MohammadTawfiqBidaki_REV_BY_TS_MohiniS_245308_1.docx (254 words)

Dear Mohammad,

You have done a pretty good job here with the essay outline. However, there are a few areas where you need to work on in the next draft. Let us look at them in detail-

Thesis Statement-

The thesis statement in the paper could be framed in a more analytical way. Let us look at how you can work on it with the help of an example.

Remember, a thesis statement has two parts- one is the claim and the other is the justification. You need to keep these in mind when you frame the thesis statement here. For example, let us assume the claim as- “Public colleges should offer free tuition.” This claim needs to be accompanied by a justification like “because it would increase access to higher education, reduce student debt, and strengthen the workforce.”

When you combine the two statements, you get the thesis statement. Try to come up with a thesis statement keeping this in mind. It needs to be of an optimum length for the reader, and is usually written in the last line of the introduction.

What is your main argument about AI? How exactly is it useful? How can it harm human relationships?

Think about these leading questions and frame an assertive thesis statement in a succinct manner.

I am sure that once you focus on these areas, your writing will look a lot more refined. I look forward to reading the revised draft. You have great potential. Keep writing. All the best!

Regards,

Mohini.

### Mehak K. — negativeaiessay_TCarusoLTI_QCC_1_REV_BY_TS_MehakK_245407_1.docx (231 words)

You have done a good job to discuss a relevant topic of the influence of artificial intelligence on society.

There are a few areas to focus on your next draft. You could add a more focused thesis statement at the end of the introduction, In the thesis, you could mention the main argument of the paper and show the key areas you will discuss. You could bring together your concerns about how AI is affecting human relationships, critical thinking, employment, and why is there a need for regulation.

Will the focus of the essay be on discussing the benefits of AI, its drawbacks or both?

How could you suggest ways to create a balance in the use of AI?

For the next steps, some of your topic sentences are a bit general. To set a clear focus, please introduce the main idea about AI’s effect on people and society you intend to discuss in the body paragraph. also try to emphasize whether an idea will be discussed as a benefit, drawback or a recommendation so that the readers know how an idea will be discussed by you in the body paragraph.

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mohini Sardar — NgocmaiChau_REV_BY_TS_MohiniS_245394_1.docx (382 words)

Dear Ngocmai,

You have done a pretty good job here with the report. However, there are a few areas where you need to work on in the next draft. Let us look at them in detail-

APA Formatting –

The paper currently is not formatted as per APA, which makes it look a little informal. You need to provide a title page before the paper which will include the title of the paper in bold, along with your name, the name of the college, the course name, instructor’s name and the date. The title details need to be centered, and should be placed in the middle of the page. Also, the date is to be written in the month-date-year format.For example, September 6, 2026These details need to be aligned to the center. Further, a running header needs to be inserted in the top right corner of the page, and it should include only the page number.

Thesis Statement-

As highlighted, the thesis statement in the paper could be framed in a precise manner to guide the discussion. Let us look at how you can work on it with the help of an example-

Remember, a thesis statement has two parts- one is the claim and the other is the justification. You need to keep these in mind when you frame the thesis statement here. For example, let us assume the claim as- “Happiness is the ability to appreciate life with contentment and optimism.” This claim needs to be accompanied by a justification like “because it enables individuals to build healthy relationships, overcome challenges, and find meaning in everyday experiences.”

When you combine the two statements, you get the thesis statement. Try to come up with a thesis statement keeping this in mind. It needs to be of an optimum length for the reader, and is usually written in the last line of the introduction.

Which performance skills did you observe at Notre Dame? How were the findings relevant to you?

Think about these leading questions and frame an assertive thesis statement in a succinct manner.

I am sure that once you focus on these areas, your writing will look a lot more refined. I look forward to reading the revised draft. You have great potential. Keep writing. All the best!

Regards,

Mohini.

### Mehak K. — OccupationalTherapyEvaluation-2-_nspape-utica.edu_UTICA_1_REV_BY_TS_MehakK_245386_1.docx (222 words)

You have done a good job to share detailed observations and assessment findings that provide a useful foundation for understanding Eloise’s abilities, developmental challenges, and participation in everyday activities.

There are a few areas to focus on your next draft. Your report includes several useful sections, but some paragraphs contain multiple ideas that could be organized more clearly. For example, the Occupational Analysis section moves from assessment scores to mental functions, sensory functions, motor abilities, and social interaction skills. Consider using clearer subheadings or separate paragraphs to separate these areas.

For the next steps, you could add clear topic sentences to further enhance the organization of ideas. For this, you could begin each paragraph with a topic sentence that identifies its main focus, and then use the observations and assessment findings to support that point.

You identify pretense/symbolic play as Eloise’s lowest-scoring domain, with an age equivalency of nine months, and mention that she imitated vocalizations and actions only a few times. How could you connect these specific observations to the assessment findings and explain their possible implications for her play participation?

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mehak K. — Osteen1_n_osteen13_brcc_3_REV_BY_TS_MehakK_245300_1.docx (268 words)

You have done a good job to discuss literary analysis of Ernest Hemingway’s “A Clean, Well-Lighted Place.” Your essay explores how loneliness and emptiness influence the characters and how the café provides them with a sense of comfort.

There are a few areas to focus on your next draft. Please make your topic sentences more specific and ensure that each body paragraph has a clear focus. For example, in your second body paragraph you begin by saying, “The way Hemingway captured the characters in his writing.” This is an incomplete sentence because it conveys an incomplete thought. You could reframe it to clearly identify the point you want to make about characterization. How could it show the views of the two waiters on loneliness?

For the next steps, please revise your paper for punctuation, capitalization, and word choice. For example, “well lite” should be “well-lit,” “empothy” should be “empathy,” and “presents” should be “presence” when referring to the older waiter’s understanding of the café’s importance.

For MLA formatting, your heading should list your name, instructor's name, course, and date in that order, with each item on a separate line. The date should follow MLA style, such as 13 October 2026. Keep the first-line indentation of each body paragraph consistent at 0.5 inches. Finally, create a separate Works Cited page rather than leaving “Cited” followed by incomplete source information.

This is a good start for your paper. I am looking forward to see how your paper would develop with these revisions. Best of luck, and feel free to reach out if you need any clarification!

Best wishes,

Mehak K.

### Mohini Sardar — StellaHofler_REV_BY_TS_MohiniS_245362_1.docx (138 words)

Dear Stella,

You have done a pretty good job here with the essay. However, there are a few areas where you

need to work on in the next draft. Let us look at them in detail-

Citations-

Apart from the in-text citations, you also need to develop a “Works Cited” page which will follow the MLA style guide. I know that citations can be daunting, which is why I will be providing a mini-lesson here on how you are supposed to format them in a more academic way. I am certain it will help you in getting your citations sorted out.

I am sure that once you focus on these areas, your writing will look a lot more refined. I look forward to reading the revised draft. You have great potential. Keep writing. All the best!

Regards,

Mohini.

## What the operator will do with your answer

The JSON is converted into template banks in `engine/review/persona.py` and
`engine/review/endnote.py`, then validated against the distribution bands above.
Patterns with slots must be usable verbatim: write sentences that read naturally
whether the slot is a word, a phrase, or a full quotation.
