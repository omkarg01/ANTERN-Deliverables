**Decision Tree :** 

**At least 3 moments where something surprised you**

1.  Decision Tree does not has any equation, they bet on like If I keep asking good questions, eventually similar outcomes will fall into the same bucket and then I esitmates the decision.  
2. Suppose we the price of house of 5000sqft is 2CR and want to predict for 8000sqft then regression can predict that by extending the line even i can guess what would be the price but for decision tree cannot do it they only know the regions they have seen. For decision tree both 5000 and 8000 sqft may fall into same category.   
3. Decision tree does not need any MSE or gradient for learning, it finds out which split is the more pure or not messy and text the decision based on it  
   

**At least 2 moments where you thought "this is exactly like regression"**

1. Regression is like a smooth curve but Decision tree instead of smooth slope its like step by step iterations, it works but not as elegant  
2. In linear regression there is loss entropy which is used to by the model to go in right direction similarly in decision tree there is gini impurity and entropy which helps the model to distinguish between 2 answers and select the one will low impurity and eventually gets the right direction  
   

**At least 1 moment where you thought "wait, this breaks something i assumed"**

1. I thought every algorithm is about some kind of mathematical equations but Decision tree is completely different it follows a simple approach of asking quality questions and creating Good set of splits with a maximum purity this method completely different from the equations mindset that I was assuming 

## **The 7-question algorithm interrogation template**

### **1\. HUMAN PROBLEM: What real-world prediction or decision does this solve?**

Ans : Decision Tree solves the problem where a sequence of questions made would result into a taking right decision. For eg:. Loan Approval, Fraud Detection etc

### **2\. HYPOTHESIS: What mathematical structure does it assume?**

Ans. Decision Tree hypothesis is reality can be separated into the meaningful groups using feature based questions. Tree believes people or features in the same region behave similarly, whereas people in different regions behave differently. Your bet is on that there exist the right sequence of the splits. 

### **3\. LOSS FUNCTION: How does it measure badness? Is this right for your problem?**

Ans:. Linear regression calculates the error, but decision tree measures the impurity in groups. There are Two metrics called Gini impurity and entropy. Gini is used to measure how impure the groups are Lesser the Ginni impurity  The better model has separated features into groups. Similarly, entropy also measures the uncertainty or impurity in the groups. But both of them have different mathematical formula to find it. 

### **4\. OPTIMIZATION: How does it find best parameters? What are the failure modes?**

Ans:. For optimization purposes, linear regression uses gradients Where at each step we are reducing the losses. But in the decision tree, the optimization method is called the greedy optimization. It does find the optimal node just for the first split And it does not think about how this split is going to act in the future. So that's what the greedy optimization is. It just thinks of the first splits only, and that is purely on the basis of the low entropy or Gini impurity. 

There are some of the failure modes we can see in this optimization method, such as 

* Early bad splits,  
* Overfitting,  
* Suboptimal tree     
* Instability in tree, 

### **5\. ASSUMPTIONS: What must be true about the data? How do I check?**

Ans:. One of the qualities that a decision tree has is that it has few assumptions as compared to other models. So, the first assumption is that perfect boundaries exist, historical Data remains relevant, future data resembles past data and Similar observations belong together.  
Or to check the assumptions, there are few of the methods such as:

* Validation performance  
* cross-validation  
* drift analysis

### **6\. OVERFITTING: When does it overfit? What regularization works?**

Ans:. Overfitting in a decision tree happens when the depth becomes excessive, which means that the height of the decision tree is very large and the leaves become very tiny. The third one is that the noise becomes the rules. 

So the regularization works in a decision tree. It controls the tree. For example, it controls the maximum depth of the tree, so it should not grow beyond the limit. It tries to keep the minimum samples per leaf, and it also tries to keep the minimum samples per split. So the regularization in decision tree is does something like stopping the tree from asking a bad-quality question. 

### **7\. PRODUCTION GAPS: What breaks between notebook and production?**

Ans. First parameter is the data drift When the time changes, the data set also changes, and the behavior of the customer changes. Because of that, as the time passes, the data becomes obsolete. In that case, data need to be updated whenever the training is done.

The second reason for which the production fails is the leakage, which means that the feature that we are going to predict already exists in the data sets. It somehow behaves like we are doing cheating. With this data leakage, the model Behaves very accurately or precisely in the training data, but it performs worst in the validation test.  

One of the failure reasons is also extrapolation failure. Let's suppose we have the data for the price of a 5,000 sq ft house. If we ask this same question to the linear regression, it can predict the price of an 8,000 sq ft apartment as well. It does by just extending the line. If we ask the same question to the decision tree, it can't, because it has never seen that data during the training, so It means that the tree may put the 1,000 sq ft into the same sample, into the same group as the 5,000 sq ft, so it somehow groups them together and predicts the value as the same, which is not accurate. 

Here is the checklist that needs to be seen before production:

1. Will the data distribution change?  
2. How often will retraining happen?  
3. What drift metrics will be monitored?  
4. Can stakeholders understand the rules?  
5. What happens when the reality changes?