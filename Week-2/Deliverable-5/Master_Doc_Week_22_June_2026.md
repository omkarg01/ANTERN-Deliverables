# \# Master Doc — Week of 22 June 2026

# 

# \*\*Name:\*\* Omkar Gujja

# 

# \---

# 

# \## Monday (22 June)

# 

# \*\*LEARNED:\*\*

# 

# The most important thing from Session 1 wasn't regression.

# 

# It was the thinking framework behind regression.

# 

# Every ML algorithm can be interrogated through the same lenses:

# 

# \- What hypothesis is being tested?

# \- What loss function are we optimizing?

# \- What assumptions are being made?

# \- What failure modes exist?

# 

# \*\*DID:\*\*

# 

# Started building thinking docs instead of collecting tutorials.

# 

# Learned the four fundamental business framings:

# 

# | Business Need | Framing |

# |---------------|----------|

# | Will it happen? | Classification |

# | How much? | Regression |

# | Which first? | Ranking |

# | When? | Survival Analysis |

# 

# \*\*OPINION:\*\*

# 

# Most ML education starts with algorithms.

# 

# It should start with business questions.

# 

# Algorithms are implementation details.

# 

# \*\*MISTAKE / CONFUSION:\*\*

# 

# I used to think choosing the algorithm was the first step.

# 

# Now it feels like framing the business problem correctly is actually the first step.

# 

# \---

# 

# \## Tuesday (23 June)

# 

# \*\*LEARNED:\*\*

# 

# Decision Trees completely break the mental model created by regression.

# 

# There is:

# 

# \- no equation

# \- no gradient descent

# \- no coefficients

# 

# Yet optimization is still happening.

# 

# \*\*DID:\*\*

# 

# Worked through Decision Tree thinking.

# 

# Started identifying moments where an algorithm transfers regression concepts and where it breaks them.

# 

# \*\*OPINION:\*\*

# 

# The best way to learn ML is not algorithm-by-algorithm.

# 

# It's concept-by-concept.

# 

# Loss.

# Optimization.

# Regularization.

# Generalization.

# 

# These ideas keep showing up in different costumes.

# 

# \*\*MISTAKE / CONFUSION:\*\*

# 

# I assumed optimization always meant gradient descent.

# 

# Decision Trees showed that's false.

# 

# \---

# 

# \## Wednesday (24 June)

# 

# \*\*LEARNED:\*\*

# 

# AI-generated content isn't considered "slop" because it is AI-generated.

# 

# It's considered slop because it lacks value.

# 

# The strongest indicators were:

# 

# \- low relevance

# \- poor information density

# \- repetitive structure

# \- weak tone

# 

# \*\*DID:\*\*

# 

# Read and analyzed the AI Slop measurement paper.

# 

# Compared research findings with LinkedIn content trends.

# 

# \*\*OPINION:\*\*

# 

# Most AI content is optimized for sounding intelligent.

# 

# Very little is optimized for teaching something useful.

# 

# \*\*MISTAKE / CONFUSION:\*\*

# 

# I previously thought verbosity made content look valuable.

# 

# The paper reinforced that verbosity often reduces value.

# 

# \---

# 

# \## Thursday (25 June)

# 

# \*\*LEARNED:\*\*

# 

# SVM is not trying to separate classes.

# 

# It's trying to maximize confidence in the separation.

# 

# The boundary matters.

# 

# But the margin matters more.

# 

# \*\*DID:\*\*

# 

# Started understanding SVM from first principles instead of memorizing support vectors and kernels.

# 

# Created intuition around why maximizing margin improves generalization.

# 

# \*\*OPINION:\*\*

# 

# Most ML explanations jump into equations too quickly.

# 

# Intuition should come before mathematics.

# 

# \*\*MISTAKE / CONFUSION:\*\*

# 

# I thought SVM was just another classification algorithm.

# 

# The margin concept makes it fundamentally different.

# 

# \---

# 

# \## Friday (26 June)

# 

# \*\*LEARNED:\*\*

# 

# RAG failures are often retrieval failures.

# 

# But many retrieval failures are actually query-understanding failures.

# 

# The system cannot retrieve what the query never expressed properly.

# 

# \*\*DID:\*\*

# 

# Studied:

# 

# \- Query rewriting

# \- Re-ranking

# \- Top-K retrieval tradeoffs

# 

# Explored why increasing Top-K is often less efficient than improving query quality.

# 

# \*\*OPINION:\*\*

# 

# Production AI systems are mostly search and systems engineering disguised as AI.

# 

# The model gets the attention.

# 

# The retrieval pipeline does the heavy lifting.

# 

# \*\*MISTAKE / CONFUSION:\*\*

# 

# My first instinct was:

# 

# "If retrieval misses the answer, increase Top-K."

# 

# Now I understand why query rewriting and re-ranking often produce better results.

# 

# \---

# 

# \## Raw Notes

# 

# \### Biggest Mental Model Shifts

# 

# 1\. Regression is not an algorithm lesson. It's a thinking framework.

# 2\. Loss functions are business decisions disguised as mathematics.

# 3\. Problem framing matters more than algorithm selection.

# 4\. Optimization does not always mean gradient descent.

# 5\. Regularization appears in different forms across algorithms.

# 6\. SVM optimizes margin, not just separation.

# 7\. RAG quality depends heavily on query understanding.

# 8\. Re-ranking often beats increasing Top-K.

# 9\. Attention is a limited resource.

# 10\. AI slop is usually low-value content, not necessarily AI-generated content.

# 11\. Production AI is mostly systems engineering.

# 12\. LinkedIn comments can create more reach than posts.

# 13\. Profile quality determines whether attention converts.

# 14\. Employers buy outcomes, not technologies.

# 15\. Consulting offers are solutions, not skill lists.

# 

