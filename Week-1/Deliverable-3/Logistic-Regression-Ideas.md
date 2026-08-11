\# Logistic Regression



\## Raw Idea 1 (Insight)



Early evidence changes probability a lot and additional evidence changes probability less. Eg. Moving 20% to 40% is easier than moving from 90% to 95% probability - i thought the impact would be same throughout



\## Raw Idea 2 (Question)



MSE ask how much your prediction is distance away from actual, Cross entropy or log loss says how confident are you and if you are wrong I will punish you - not sure how log loss answer this question



\## Raw Idea 3 (Question)



Both uses gradient descent for optimization - I know how the gradient descent works in the case of linear regression i know the equation as well but not sure what is the equation for logstic regress and how gradient descent works here



\## Raw Idea 4 (Observation)



My assumption was that I have to prepare the model once and deploy it and job is done, but the reality is model needs to evolve as the time - I never thought of it in this way, this gave me some new perspective



\## Raw Idea 5 (Question)



Logistic Regression assumes the evidence accumulates linearly. Positive signals increases confidence and negative signals decreases confidence. This evidence is transforms into probability using and S-shaped curve.

So its like: Features > Linear Addition >Prediction - not sure how does S - shaped curve is formed i just now it theoritically



\## Raw Idea 6 (Question)



Optimization failure mode : 1. Learning rate too high, 2. Learning rate too low, 3. Poor Scaling, 4. Weak Regularization, dont have practical understanding how this failure mode occurs



\## Raw Idea 7 (Question)



Logistic regression has many assumptions like there should be multicollinearity which means all features should has different information

there are many other assumption on which logistic regression depends on but we always have to do diagnostic checks there are methods such as: Correlation matrix, VIF Variance Inflation Factor, Calibration Curve, Feature Inspection - so while developing the mode we should have proper understanding of how this methods works and how it helps to clear the assumptions.



\## Raw Idea 8 (Question)



I know about overfitting in linear regression which means straight line fitting to all data points and trying to memorize it, I know the how so visually in the graph, but don't have much idea about how the overfitting looks visually in the case of logistic regression



\## Raw Idea 9 (Question)



Don't know how the regularization, like L1 and L2, helps in the logistic regressions.



\---



\# Selected 5 Ideas



\## Selected Idea 1 (Question)



MSE ask how much your prediction is distance away from actual, Cross entropy or log loss says how confident are you and if you are wrong I will punish you - not sure how log loss answer this question



\## Selected Idea 2 (Question)



Logistic Regression assumes the evidence accumulates linearly. Positive signals increases confidence and negative signals decreases confidence. This evidence is transforms into probability using and S-shaped curve.

So its like: Features > Linear Addition >Prediction - not sure how does S - shaped curve is formed i just now it theoritically



\## Selected Idea 3 (Insight)



Early evidence changes probability a lot and additional evidence changes probability less. Eg. Moving 20% to 40% is easier than moving from 90% to 95% probability - i thought the impact would be same throughout



\## Selected Idea 4 (Question)



Logistic regression has many assumptions like there should be multicollinearity which means all features should has different information

there are many other assumption on which logistic regression depends on but we always have to do diagnostic checks there are methods such as: Correlation matrix, VIF Variance Inflation Factor, Calibration Curve, Feature Inspection - so while developing the mode we should have proper understanding of how this methods works and how it helps to clear the assumptions.



\## Selected Idea 5 (Observation)



My assumption was that I have to prepare the model once and deploy it and job is done, but the reality is model needs to evolve as the time - I never thought of it in this way, this gave me some new perspective



