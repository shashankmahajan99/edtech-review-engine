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

### janeen_REV_BY_TS_RaunakB_243347_1.docx

Dear Janeen,
Thank you for submitting your paper.
There are some suggestions that may help improve the quality of the paper:

Thesis and Main Argument:
Your introduction discusses the financial problems of students, but your thesis could be tighter. You might want to ensure that you give your thesis a statement of your opinion while at the same time giving hints of your major supporting points, such as access to college, debts, and financial flexibility. This will help make it more straightforward for your audience to grasp the content of the unit.

Evidence and Analysis:
You give a number of relevant research studies and statistics, especially in the part on enrolment issues and student debt but some paragraphs skip too quickly from one piece of evidence to the other. Once you present the results of some research study of interest, you need to elaborate more on what the data can prove or what particular claim of this paragraph is supported by it.

Structure and Counterargument:
The section on the drawbacks of free education introduces a crucial element to the essay. You may want to link this section to your position by elaborating on how these drawbacks either contradict your view or enhance

I hope you find the feedback helpful.
All the best.
Raunak Banga

### andrea goblet.docx

Dear Andrea,
Thank you submitting your draft. Please pay attention to the following domains:

Introduction and Assertion of Thesis: The introduction provides the information about the work and also offers the general outline of its aim to the readers. However, the core of rhetorical analysis is not expressed with great clarity at this moment. You may consider pointing out the rhetorical tactics in your work and their connection with each other.

Analysis and Evidence: The body of your work reveals several situations from Trimble’s life along with the emotional appeals and facts. Nevertheless, there is the need to explore the link between the rhetorical tactics and the examples provided in the body paragraphs. After providing an example, it is important for you to mention how the used example influences the audience and helps to prove the main idea of the paragraph.

Clarity and Proofreading: The draft contains numerous cases of spacing, punctuation and spelling mistakes that hamper the understanding of your thoughts. Hence there is a need to make the final proof-reading process more careful and thorough.

I hope you find the feedback useful.
All the best.
Raunak Banga

### kiran mitra.docx

Dear Kiran,
Thank you for submitting in your paper. You need to focus on:
Thesis and overall focus:
Your introduction does a great job of describing the problem of antimicrobial resistance. However, your thesis is a little vague and does not clearly preview the direction of your essay. Since you only go into detail in three areas, I suggest you broaden your thesis statement to include each of those three areas in your approach. This will help to clarify the focus of your paper for the reader.

Evidence and analysis:
You have described the stewardship-program study, the ozone-treatment study, and bacteriophage research. However, in some places, it seems like you are jump from these results to other ideas without giving the reader a bit of time to understand the implications and meaning of these results. When you do present some solid evidence, try to provide some analysis of what this means and how this leads to your main point in that paragraph. This will help to keep your paper at an analytical level instead of a more descriptive level.

Conclusion and synthesis:
You mention the 3 approaches in your conclusion. However, you only restate the approaches but do not add anything further. Instead, maybe you could talk about how these 3 approaches need to be followed to effectively address antimicrobial resistance. I think this would help the reader come to with a strong conclusion about your main points and ideas.

I hope this feedback is helpful.
All the best.
Raunak Banga

## What the operator will do with your answer

The JSON is converted into template banks in `engine/review/persona.py` and
`engine/review/endnote.py`, then validated against the distribution bands above.
Patterns with slots must be usable verbatim: write sentences that read naturally
whether the slot is a word, a phrase, or a full quotation.
