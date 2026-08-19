# Personalised Outreach Campaign

## 1. Four-Message Sequence

### Message 1 --- Initial Outreach

Hi {{first_name}},

I came across {{company_name}} while researching how FinTech AI teams
are applying AI to {{specific_product_or_workflow}}.

With {{recent_trigger}}, I was curious about one part of the workflow:
as {{specific_document_workflow}} moves into production, is the harder
problem still extraction and retrieval accuracy, or has it shifted
toward things like evidence traceability, evaluation, and handling
uncertain cases?

I'm building in this problem space and would genuinely value your
perspective on where the real bottleneck is for teams like yours.

------------------------------------------------------------------------

### Message 2 --- Follow-up 1: Technical Insight

Hi {{first_name}},

I've been thinking further about {{company_name}}'s
{{specific_workflow}}.

One pattern I'm exploring is that document AI becomes a different
engineering problem once it enters a financial workflow. Retrieval
quality matters, but so do structured outputs, evidence linking,
evaluation, conflicting information across documents, and escalation
when the system is uncertain.

For {{company_name}}, my hypothesis is that
{{company_specific_hypothesis}} may be one of the difficult parts of
making the workflow reliable at scale.

I may be wrong about the bottleneck---curious whether this is close to
what your team sees.

------------------------------------------------------------------------

### Message 3 --- Follow-up 2: Proof of Capability

Hi {{first_name}},

I've been building a financial document intelligence prototype around
this problem.

The current workflow focuses on structured extraction, source-linked
answers, cross-document comparison, and routing uncertain outputs for
human review rather than treating every model response as equally
reliable.

Looking at {{company_name}}, I mapped how a similar approach could apply
to {{company_specific_use_case}}, particularly around
{{specific_reliability_or_workflow_problem}}.

If useful, I can send you the prototype and the short workflow map. No
meeting needed---I'd be interested in whether the approach matches the
real problem or misses something important.

------------------------------------------------------------------------

### Message 4 --- Follow-up 3: Close the Loop

Hi {{first_name}},

I'll close the loop here.

I'm continuing to build around reliable document intelligence for
financial workflows and using conversations with FinTech teams to
understand where the real production bottlenecks are---whether that's
extraction quality, traceability, evaluation, integration, or something
else entirely.

If {{company_specific_problem}} becomes relevant for {{company_name}},
I'd be happy to share what I've built and the workflow analysis behind
it.

Either way, thanks for reading.

## 2. Campaign Rationale

### Why the Messaging Should Work for This ICP

The target ICP is early-growth and growth-stage FinTech AI companies in
the UK and US with approximately 20--200 employees, primarily targeting
CTOs, Founders, and Heads of AI.

The messaging assumes these recipients already understand AI and may
already have AI capabilities in their products. Therefore, the campaign
does not make a generic pitch about adopting AI. Instead, it focuses on
making financial document intelligence reliable enough for production
workflows.

The messaging explores structured extraction, evidence traceability,
cross-document comparison, evaluation, uncertainty handling, and human
review.

The campaign adapts the value angle by role:

-   **CTO:** architecture, reliability, integration, and production
    efficiency.
-   **Head of AI:** evaluation, extraction and retrieval quality,
    uncertainty handling, and model reliability.
-   **Founder:** workflow speed, operational efficiency, customer value,
    and product differentiation.

The sequence builds trust gradually: company-specific observation and
informed question, technical insight, proof of work and company-specific
application, then a respectful close.

### Why the Recipient Has a Reason to Reply

The initial message asks the recipient to respond to a specific workflow
hypothesis rather than asking for a meeting or selling a service.

The recipient can confirm the problem, correct the hypothesis, ask to
see the prototype or workflow map, or refer the conversation to a more
relevant person.

The CTA remains low-friction: "If useful, I can send you the prototype
and the short workflow map. No meeting needed."

### Personalisation Fields

  ------------------------------------------------------------------------------------
  Field                                            Purpose
  ------------------------------------------------ -----------------------------------
  `{{first_name}}`                                 Identifies the recipient

  `{{company_name}}`                               Connects the message to the company

  `{{recipient_role}}`                             Determines the value angle

  `{{specific_product_or_workflow}}`               Shows understanding of the product

  `{{recent_trigger}}`                             Establishes why now

  `{{specific_document_workflow}}`                 Identifies the relevant workflow

  `{{specific_workflow}}`                          References the workflow in
                                                   follow-up messaging

  `{{company_specific_hypothesis}}`                Introduces a testable problem
                                                   hypothesis

  `{{company_specific_use_case}}`                  Connects the prototype to the
                                                   company

  `{{specific_reliability_or_workflow_problem}}`   Makes the proof of work relevant

  `{{company_specific_problem}}`                   Personalises the closing message
  ------------------------------------------------------------------------------------

**Campaign rule:** If the company-specific workflow, trigger, or problem
hypothesis cannot be supported by credible public information, the
message should not be sent with that claim.

### Expected Reply Rate and Basis

The working hypothesis is an **8--15% reply rate**. This is a campaign
planning assumption, not a guaranteed benchmark. The basis is the narrow
ICP, company-specific research, defined technical problem family, and
low-friction conversational CTA.

The first batch is a learning experiment testing problem relevance,
recurring bottlenecks, role response patterns, company-type response
patterns, and whether the prototype creates enough curiosity to continue
the conversation.

### Response Classification

1.  **Positive interest** --- asks for the prototype, workflow map,
    conversation, or more information.
2.  **Problem confirmed, timing wrong** --- confirms relevance but has
    no immediate need.
3.  **Problem correction** --- explains that the real bottleneck is
    different.
4.  **Referral** --- redirects the conversation to another person.
5.  **Not relevant or negative** --- the problem or offer is not
    relevant.

Problem-correction responses are treated as useful research signals.

### What Changes if the Campaign Underperforms

-   **Low connection acceptance or open rate:** Review company
    selection, recipient selection, and first-line relevance.
-   **Messages viewed but low reply rate:** Test a different problem
    hypothesis or lower-friction CTA.
-   **Replies but little prototype interest:** Improve proof of work or
    choose a problem closer to operational pain.
-   **Repeated problem corrections:** Update the campaign around the
    bottleneck appearing most frequently.
-   **One company type responds better:** Narrow the campaign segment
    further.
-   **One role responds better:** Prioritise that role in the next
    campaign batch.

## 3. SBL Configuration

### Messaging and Personalisation Fields

The campaign uses the four-message sequence built around financial
document intelligence. Each lead must be enriched with the
personalisation fields above before entering the sequence.
Company-specific fields must be based on credible public evidence.

### Follow-up Sequence and Timing

  Day      Action
  -------- ----------------------------------
  Day 1    Initial message
  Day 4    Follow-up 1: technical insight
  Day 8    Follow-up 2: proof of capability
  Day 14   Follow-up 3: respectful close

The first test targets **10--15 new prospects per week** to maintain
genuine personalisation and learn from replies before increasing volume.

### Sending Schedule and Campaign Settings

Messages will be sent Tuesday to Thursday during the recipient's local
working hours.

-   Target only companies matching the ICP.
-   Prioritise CTOs and Heads of AI for highly technical angles.
-   Include Founders where the company is smaller and the Founder
    remains close to product and technical decisions.
-   Do not send all prospects simultaneously.
-   Review responses after each batch before scaling.
-   Avoid sending multiple people at the same company the same sequence
    at the same time.

The campaign optimises for quality of conversations and learning signals
rather than maximum message volume.

### Stop Conditions

The sequence stops immediately when the recipient replies, asks not to
be contacted, provides a referral, is found to be outside the ICP, the
trigger becomes irrelevant, or a genuine conversation begins through
another channel.

A positive reply moves the lead into manual conversation. A negative
reply receives no further automated messages.

### Reply Handling

  -----------------------------------------------------------------------
  Response Type                       Action
  ----------------------------------- -----------------------------------
  Positive interest                   Respond manually and continue
                                      around their problem

  Requests prototype                  Send proof of work with brief
                                      context

  Problem confirmed, timing wrong     Record the problem and ask
                                      permission for a later follow-up

  Problem correction                  Ask one useful follow-up question
                                      and update campaign learning

  Referral                            Thank them and contact the referred
                                      person with context

  Not relevant                        Record the reason and stop the
                                      sequence

  No reply                            Continue the scheduled sequence
                                      until Follow-up 3
  -----------------------------------------------------------------------

The first response should not automatically turn into a consulting
pitch. The immediate goal is to understand the problem, establish
relevance, and determine whether there is a useful next step.
