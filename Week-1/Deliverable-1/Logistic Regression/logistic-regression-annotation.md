**Logistic Regression:** 

**At least 3 moments where something surprised you**

1. Linear Regression is about the predicting the value of unit e.g.+50% revenue next

month whereas the Logistic Regression is about calculating the probability of incident  
e.g. 90% probability of customer getting churn

2\.   Early evidence changes probability a lot and additional evidence changes probability less. Eg. Moving 20% to 40% is easier than moving from 90% to 95% probability 

3\.  Logistics regression is about classification but in fact it is like a probability prediction where classification is a done after the model predates the probability for example first model will predict probability is 85% then it will classify like more than 85% the customer will churn and less than 85% the customer you will not churn 

4\. MSE ask how much your prediction is distance away from actual, Cross entropy or log loss says how confident are you and if you are wrong I will punish you

**At least 2 moments where you thought "this is exactly like regression"**  
1\.  MSE punishes the more to the point which farther from actual line similarly Cross entropy punishes the more to the most confident but wrong evidence   
2\. Both uses gradient descent for optimization 

**At least 1 moment where you thought "wait, this breaks something i assumed"**  
1\. My assumption was that I have to prepare the model once and deploy it and job is done, but the reality is model needs to evolve as the time changes the features that were used to find loan defaults during 2021 (COVID time) does not work now in 2026, today some other features need to be considered. Logistic regression model weights should be adjusted every month and retrained the model quarterly atleast. This makes the model robust and nearly accurate.

## **The 7-question algorithm interrogation template**

### **1\. HUMAN PROBLEM: What real-world prediction or decision does this solve?**

Ans : Logistic Regression gives the prediction of how likely the event will occur and the output is probability. Eg. Lead 1 \=\> 92% probability of conversion, So this algorithm answers in binary Yes/No, will Churn/ will not Churn, etc

### **2\. HYPOTHESIS: What mathematical structure does it assume?**

Ans. Logistic Regression assumes the evidence accumulates linearly. Positive signals increases confidence and negative signals decreases confidence. This evidence is transforms into probability using and S-shaped curve.   
So its like: Features \> Linear Addition \>Prediction 

### **3\. LOSS FUNCTION: How does it measure badness? Is this right for your problem?**

Ans:. Logistic Regression uses Cross-Entropy Loss (Log Loss). It measures how far the predicted probability is from the actual outcome. It heavily penalizes predictions that are confidently wrong and penalizes less when the model is uncertain or slightly wrong.

For example:

* If the model predicts 99% conversion probability, but the client does not convert, the loss is very high.  
* If the model predicts 42% conversion probability, and the client does not convert, the loss is much lower.

### **4\. OPTIMIZATION: How does it find best parameters? What are the failure modes?**

Ans:. Logistic regression uses Gradient Descent for the optimization. It starts with some random weights an finds the loss with this weights and in next iteration it adjust the weights based on learning rate and then computes the loss with this updated weights. It does this until there is no major loss reduction or also called as convergence point. 

Failure mode: 

1. Learning rate too high  
2. Learning rate too low  
3. Poor scaling  
4. Weak regularization  
5. Leakage  
6. Multi-collinearity (which means the 2 or more features with similar meaning)  
7. Convergence warning (this can happen due to poor features scaling) 

### **5\. ASSUMPTIONS: What must be true about the data? How do I check?**

Ans:.   
Logistic regression assumes:

1. There should be low multicollinearity which means all features should has different information. (Its about features)

 

2. Knowing one data point should not automatically tell you something about another data point. (Its about data point)  
3. Linear relationship in log-odds: Logistic Regression assumes that feature contributions can be added linearly as evidence before converting them into a probability.

Diagnostic Checks: 

1. Correlation Matrix \- it use to measure the relation between the 2 features. Correlation ≈ 1.0 means 2 features almost serves the same purpose. Its the case of multicollinearity.  
2. VIF(Variance Inflation Factor) Analysis: Correlation matrix gives how 2 features are related to each other but VIF understands the relation between 2 or more than 2 features relations. Eg. Experience, Age, Job Level not serving any meaningful purpose thats obvious High Experince comes as the age increases and Job level or position increases.  
3. Calibration Curves: It says are the predictions closer to the reality. If prediction is 80% and out of the 100 customers 80 converted then we can see the model is calibrated quite well whereas if 40 converted we can say model is quite over confident.  
4. Feature inspection: to check whether the coefficient makes the business sense. For eg. heck whether the learned coefficients align with business logic and domain knowledge (e.g., higher income should generally increase approval probability). If coefficients look counterintuitive, it may indicate issues such as multicollinearity, data leakage, or poor data quality. 

### **6\. OVERFITTING: When does it overfit? What regularization works?**

Ans:. Logistic regression overfits when:

* Too many features  
* Too little data  
* Highly correlated features  
* Noise-heavy features  
* leaked predictors 

Use L2 when many features useful   
Use L1 for feature selection it removes the unimportant features from the Model,  
Use Elastic Net when features are many and are related to each other, Its the combination of both L1 and L2.  

### **7\. PRODUCTION GAPS: What breaks between notebook and production?**

Ans. 

1. Data drift: if predicting the will the loan default or not for that if use the old data of 2021(COVID time) in current time 2026\. Even if the probability is high it will not relevant to current market condition  
2. Calibration drift: If predicted probabilities stops matching reality. The ranking may be good but the probabilities becomes misleading.  
3. Data leakage: The model uses information during training that won't be available when making real predictions. For eg. if we build loan default prediction model and it has feature called “Days Past Due” but this can be known only after the loan has been issued. So the model may perform great during training but unusable in production.  
4. Threshold Problems: Business objectives changes but the threshold remaining the same. Let's suppose that initially we put a threshold of 50, and if it is greater than 50%, then we should call the customer, but, if the sales team gets smaller, we have to target only highly qualified customers. We should increase the threshold to 80%, but instead of increasing the threshold percent, we just keep it as it is and make no changes to the threshold so the business resources will be wasted here as it will target the unqualified customers as well   
5. Explainability Requirements: Which means that, let's suppose if the model predicted some value and we are not able to explain the reason for what this prediction value stands for; then the stakeholder might not use this model. They will have less trust in the model, as we are not able to explain the purpose of this probability value what it stand for. 