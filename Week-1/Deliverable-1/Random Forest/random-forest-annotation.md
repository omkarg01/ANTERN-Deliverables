**Random Forest :** 

**At least 3 moments where something surprised you**

1. I thought that the Random Forest is the single huge Decision tree but i was surprise when came to know that it is a combination of multiple Decision Tree.  
2. Every model requires regularization to simplify the weights, and the same is the case with the random forest, and   
   it simplifies by :   
- Min Samples Per Leaf  
- Number of Features Considered  
- Number of Trees  
- Max Depth

  Forest has the built-in regularization. Randomness itself acts as the regularizer.   
  Each tree has: sees different data and sees different features. This prevents synchronized overfitting.  
    
3. Every model has assumptions, and random forest is no exception. One thing surprised me: linear regression assumes more than the random forest. For example, linear regression assumes linearity, homoscedasticity, and normal residuals, but random forest has very few assumptions. I thought that, since random forest is such a huge forest of multiple trees and each tree will have depth, it is a complex structure in itself, so there will be more assumptions for random forest. The reality is that the random forest has very few assumptions compared to the linear regression models.  
   This being said it still has a few assumptions Causes production failures. 

**At least 2 moments where you thought "this is exactly like regression"**

1. The loss function in the Linear regression and that of in random forest mostly work in a similar fashion. Why did I say in a similar fashion? Although both of the formulas, like MSE and the ginni or entropy, have completely different mathematical formulas, while Inputs that need to be considered while calculating these loss It's more about business Not just a mathematical function. Example: if the model predicts that 98 will not default and the 2% will default, but the 2% could cost an overall loss of 2 crore rupees. From the business perspective, that 2 crore will be much more. So, here, although the prediction is 98%, from a business standpoint, it's not meaningful, or it will not draw some good outputs. In fact, it will make losses for the company, so the model will be completely useless. Business becomes the most important standpoint while calculating the loss functions In both the models, Random Forest and the Linear Regression.    
2. Hypothesis is a core principle of the linear regression as well as the random forest. The model fails if the hypotheses are made wrong. For example, if we frame “how much money we might lose” as "will the loan default or not?"  We will fail to make the distinction between the 10,000 and 10 crore rupees eventually. So that's why principal It's the same, but the execution is different between these two models. 

**At least 1 moment where you thought "wait, this breaks something i assumed"**

1. At first, I assume that random forest will have multiple trees, but each of the trees will have all the same features But later on I got to know that all the trees have different kinds of features. Some of the features could be in one tree, and some other features could be hidden from the first tree and be in the second tree. There will be a diversity in the trees. There was actually one discovery behind this: the scientist said that a random forest with weaker but diverse trees beats much more often than a forest with stronger but identical trees. And the reason behind this diversity is that, statistically, diversity in health always reduces the errors. 

## **The 7-question algorithm interrogation template**

### **1\. HUMAN PROBLEM: What real-world prediction or decision does this solve?**

Ans : Although the decision tree was good for making the predictions, it was unstable. To compensate for this issue, we have used random forest, and what it does is it takes the multiple decision trees and does the voting. And the tree that has the highest number of the votes will be used for the final result. The outcome depends on many factors, and a single role is not reliable.   
So the main problem it solves: it does not create a better rule. In fact, it solves the problem of making reliable rules. 

### **2\. HYPOTHESIS: What mathematical structure does it assume?**

Ans. Random forest assumes that many decision trees voting together form reliable answers instead of depending on a single decision tree. Every tree of a decision tree is a hierarchical-based rule system. Overall, this forest assumes that many imperfect rule-based systems outperform a single strong rule-based system.   
So the question that we need to ask ourselves That does. Our problem contains the multiple pathways to come at the one single outcome. If the answer is yes, then this random forest is best.   
The regression says: can a single line define the reality?   
And the random forest says Can a many rule-based system define the reality?  

### **3\. LOSS FUNCTION: How does it measure badness? Is this right for your problem?**

Ans:. Random forest, have the same ginni impurity and entropy. They measure how much impure a decision tree is. The important question from the business objective is For example, a loan defaults may represent   
2% of customers  
20% of losses 

A purity-based model may still miss expensive defaults.  
To ask: What is more important for the business, an expensive rejection or an expensive approval?   
And the evaluation strategy should reflect that.

### **4\. OPTIMIZATION: How does it find best parameters? What are the failure modes?**

Ans:. A random forest does not have gradient descent, learning rate, and a back-propagation. Each tray repeatedly finds the best split and then does the splitting, and it performs these subprocesses repeatedly using the greedy optimization. And then many trees will be formed, and all these trees do the voting. From this voting, the tree which has got the maximum vote is the prediction that will be considered at the end.   
In random forest, there are many failure modes, such as:

* Trees may become highly correlated.  
* Forest may become too large.  
* Trees may overfit the noise.  
* Data drift and change patterns.

### **5\. ASSUMPTIONS: What must be true about the data? How do I check?**

Ans:. Random forest has fewer assumptions than linear regression, but not zero assumptions. 

Assumption 1: Featured data resembles the historical data.

Assumption 2: Features contain meaningful signal.

Assumption 3: Labels are trustworthy.

Assumption 4: Training data represents production reality.

### **6\. OVERFITTING: When does it overfit? What regularization works?**

Ans:.  Random forest overfits when:

* trees become too deep  
* data set is too small  
* features are noisy  
* labels contain errors

Although random forest reduces variance compared to a single tree, variance reduction is not equal to overfitting elimination. 

What regularization works?   
1\. max depth : How deep a tree can grow? A small tree means simple rules, so if we have a deep tree, then it will memorize the data. So to make it a simple tree, we have to not make an extremely complicated rule chain. 

2\. min Sample Split : How many samples must exist before creating another split? Example: if If a node contains 100 rows then we can split, but if a node contains only two rows, then, in fact, we should avoid splitting it further. So to make a simple tree, don't create a decision based on a tiny amount of data. 

3\. Min sample leaf: What's the minimum number of rows allowed in a final leaf? If the final leaf Has one customer, then tree has memorized one person, which is a bad tree. On the other hand, if the final leaf has 20-50 customers, then this means it's more reliable. So to make the trees simple, every rule must apply to a meaningful group of people.

4\. Max features: At each split, how many features can the tree consider? Suppose 20 features without restriction. Every tree sees all 20\. All trees become similar. Whereas random forest wants diversity, if each split sees only 4 random forests, then what happens is that all the trees will think differently. So we have to prevent every tree from chasing the same pattern.

5\. Limiting tree count: Many trees in the forest? A forest with the 10 trees is called a simple forest, and a forest with the 5,000 is huge forest. More trees reduce variance but eventually lead to a very little improvement, but it consumes much more memory and latency. So, to keep the simple tree, we don't have to build an unnecessarily huge tree. 

6\. Feature selection: Suppose we consider the following features:

* Income  
* Debt  
* Credit Score  
* Age  
* Favourite Color  
* Laptop Brand

The last two are useless. If we remove those last two and create new features:

* Income  
* Debt  
* Credit score  
* Age

this will eventually reduce so much noise. So this will give the forest of very few distractions. 

### **7\. PRODUCTION GAPS: What breaks between notebook and production?**

Ans. There are multiple reasons for which the model breaks in the product. 

1. Data drift: Data drift means that the pattern in the data, or the information that we are deriving from the data, will change eventually. For example, customer behavior changes, the economy changes, and regulations change, so with that, the forest becomes eventually outdated.   
2. Leakage: So if a feature accidentally contains any future Information, then the training metrics becomes meaningless.   
3. Explainability: Let's suppose that if a stakeholder asks why this loan was rejected, a random forest is much harder to explain than regression or a single tree.  
4. Latency : 500 trees are much slower than a linear regression and a single decision tree. We should make the sufficient tree such that it has very low latency. Or else the production will not accept it.   
5. Monitoring: So the quality of the forest deteriorates without monitoring. So, we should always keep on monitoring and make necessary changes. 