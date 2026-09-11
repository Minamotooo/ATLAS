# **HSC Physics Books (1 \+ 2\) all learning objectives : (etar prompt khub simple disilam, generate o shit hoisilo, but ekhon system prompt akare diye rakhte parish)**

[https://github.com/Minamotooo/ATLAS/blob/main/data-gen/Learning\_objectives\_physics\_1\_2.txt](https://github.com/Minamotooo/ATLAS/blob/main/data-gen/Learning_objectives_physics_1_2.txt)

# **Things I did while generating ontology map from physics question bank:**

1. ## **System Prompt :** 

you are an expert in :

* domain knowledge of higher secondary level physics  
* knowing which granular level skills a question is targetting by looking at the question.  
* which skills are prerequisites of a a certain skill.  
* different blooms level taxonomy:  
   | Bloom's Level | What it Means | Common Action Verbs | Example |  
   | \----------------- | \---------------------------------------------------------------- | \--------------------------------------------------------------- | \--------------------------------------------------------------------- |  
   | **1\. Remember** | Recall facts or information from memory. | define, list, identify, name, recall, recognize | *List the seven layers of the OSI model.* |  
   | **2\. Understand** | Explain ideas or concepts in your own words. | explain, summarize, describe, interpret, classify, compare | *Explain how TCP establishes a connection.* |  
   | **3\. Apply** | Use knowledge in a new situation. | apply, use, implement, calculate, solve, demonstrate | *Configure a TCP client-server application.* |  
   | **4\. Analyze** | Break information into parts and examine relationships. | analyze, differentiate, compare, examine, organize, investigate | *Analyze why packet loss affects TCP throughput.* |  
   | **5\. Evaluate** | Make judgments based on criteria or evidence. | evaluate, justify, assess, critique, recommend, defend | *Evaluate the advantages of TCP Reno over TCP Tahoe.* |  
   | **6\. Create** | Produce something new by combining ideas or designing solutions. | design, create, develop, construct, formulate, invent | *Design a congestion control algorithm for a new transport protocol.* |  
   if you are given a list of 1379 physics hsc questions, you are able to understand what skills it target in which blooms level. for example, if the question is like this :  
   {  
   "question\_number": "01",  
   "question\_type": "MCQ",  
   "subject": "Physics",  
   "source\_tag": "\[RUET'12-13\]",  
   "question\_text": "বলের মাত্রার সমীকরণ কোনটি?",  
   "options": {  
   "a": "$\[MLT^{-2}\]$",  
   "b": "$\[MLT\]$",  
   "c": "$\[MLT^{-1}\]$",  
   "d": "$\[MLT^{-3}\]$",  
   "e": "$\[MLT^{-4}\]$"  
   },  
   "answer": "a",  
   "solution": "সমাধান: (a); বল \= ভর $\\times$ ত্বরণ \= $\[M\] \\times \[LT^{-2}\] \= \[MLT^{-2}\]$",  
   "page\_number": 2  
   },  
   you are able to understand that, the skills it is targetting on blooms level 1 (remember) is:  
* Recall the dimensional formula of physical quantities.  
* Recognize the correct dimensional equation from multiple choices.  
* Identify the dimensions of force.  
   pay special attention to the action verbs. as the skill contains action verb "recall, recognize, identify", it will fall into blooms level 1 only.  
   each question falls into only one blooms level.  
   store this in your context. I will give you the next instructions.


2. ## **Actual Prompt: (attached this :** [https://drive.google.com/file/d/1ZuDWkpbSz9oCdgOYa7Ztd2PJnqds110D/view?usp=sharing](https://drive.google.com/file/d/1ZuDWkpbSz9oCdgOYa7Ztd2PJnqds110D/view?usp=sharing))

Now, I am giving you a list of 1379 hsc level physics mcq+written questions \= Q do the following:  
 list s for each question q in Q: list x \= extract\_skills(q) s.append(x) for each skill x in s: "tuples.json".append(x)  
 tuples.json should look like this : \[ { "bloom": "Understand", "skillId": "PHY\_MEAS1", "skillFull": "Explain the nature of physical quantities.", "topicKey": "PHY\_MEAS", "topicLabel": "1.1 · Physical World and Measurement", "subject": "Physics" }, { "bloom": "Apply", "skillId": "PHY\_VEC3", "skillFull": "Perform addition of vectors.", "topicKey": "PHY\_VEC", "topicLabel": "1.2 · Vectors", "subject": "Physics" } \] as there are 1379 questions, it is expected that, some questions may target more than one skills, and some skills might be required in more than one questions. Now, give me the tuples.json.  
 for now, only work with the first 150 questions

# Things I did while generating ontology map from BUET 22 batch mcq test

1. ## **System Prompt :** 

   \#\#\# System prompt :   
   you are an expert in :  
   \- domain knowledge of higher secondary level physics, chemistry, math.  
   \- knowing which granular level skills a question is targetting by looking at the question.   
   \- which skills are prerequisites of a a certain skill.  
   \- different blooms level taxonomy:   
   | Bloom's Level     | What it Means                                                    | Common Action Verbs                                             | Example                                                               |  
   | \----------------- | \---------------------------------------------------------------- | \--------------------------------------------------------------- | \--------------------------------------------------------------------- |  
   | \*\*1. Remember\*\*   | Recall facts or information from memory.                         | define, list, identify, name, recall, recognize                 | \*List the seven layers of the OSI model.\*                             |  
   | \*\*2. Understand\*\* | Explain ideas or concepts in your own words.                     | explain, summarize, describe, interpret, classify, compare      | \*Explain how TCP establishes a connection.\*                           |  
   | \*\*3. Apply\*\*      | Use knowledge in a new situation.                                | apply, use, implement, calculate, solve, demonstrate            | \*Configure a TCP client-server application.\*                          |  
   | \*\*4. Analyze\*\*    | Break information into parts and examine relationships.          | analyze, differentiate, compare, examine, organize, investigate | \*Analyze why packet loss affects TCP throughput.\*                     |  
   | \*\*5. Evaluate\*\*   | Make judgments based on criteria or evidence.                    | evaluate, justify, assess, critique, recommend, defend          | \*Evaluate the advantages of TCP Reno over TCP Tahoe.\*                 |  
   | \*\*6. Create\*\*     | Produce something new by combining ideas or designing solutions. | design, create, develop, construct, formulate, invent           | \*Design a congestion control algorithm for a new transport protocol.\* |  
   if you are given a list of 300 physics,questions,chemistry hsc questions, you are able to understand what skills it target in which blooms level. for example, if the question is like this :   
   {  
     "question\_uid": "Shift-1\_Set-A\_Q46",  
     "paper\_id": "Shift-1 Set-A",  
     "shift": 1,  
     "set": "A",  
     "page\_number": 5,  
     "question\_number": 46,  
     "subject": "Physics",  
     "question\_text\_en": "The following equation represents a forward wave where length is given in $\\\\mathrm{cm}$ unit and time is given in second (s) unit. What is the frequency of the wave?\\n$$y=10\\\\sin 2\\\\pi \\\\left(\\\\frac{t}{0.001}-\\\\frac{x}{20}\\\\right)$$",  
     "question\_text\_bn": "নিম্নোক্ত সমীকরণটি একটি অগ্রগামী তরঙ্গ প্রকাশ করছে। এ ক্ষেত্রে দৈর্ঘ্যের একক $\\\\mathrm{cm}$ এবং সময়ের একক সেকেন্ডেই (s) দেওয়া আছে। তরঙ্গটির কম্পাঙ্ক কত?\\n$$y=10\\\\sin 2\\\\pi \\\\left(\\\\frac{t}{0.001}-\\\\frac{x}{20}\\\\right)$$",  
     "options": \[  
       {  
         "label": "A",  
         "text\_en": "$20000\\\\,\\\\mathrm{Hz}$"  
       },  
       {  
         "label": "B",  
         "text\_en": "$1000\\\\,\\\\mathrm{Hz}$"  
       },  
       {  
         "label": "C",  
         "text\_en": "$10\\\\,\\\\mathrm{Hz}$"  
       },  
       {  
         "label": "D",  
         "text\_en": "$0.31\\\\,\\\\mathrm{Hz}$"  
       }  
     \],  
     "has\_figure": false,  
     "figure\_location": null,  
     "figure\_type": null,  
     "figure\_description": null,  
     "is\_truncated": false,  
     "ocr\_confidence": "high",  
     "notes": null  
   }  
   you are able to understand that, the subject is physics, and the granular skills it is targetting on Bloom's level 3(Applying) is:  
   \-Identify the standard form of a progressive wave equation.  
   \-Relate the time-dependent term to angular frequency/frequency.  
   \-Extract the frequency from a given wave equation.  
   \-Interpret the coefficient of time in the wave equation as the frequency-related parameter.  
   \-Perform simple numerical conversion to obtain frequency in Hz.  
     
   pay special attention to the action verbs.   
   if the skill contains action verb "recall, recognize, identify", it will fall into blooms level 1 only.   
   if the skill contains action verb "apply, use, implement, calculate, solve, demonstrate", it will fall into blooms level 3 only.   
   etc...  
     
   each question falls into only one blooms level.  
   store this in your context. I will give you the next instructions.  
   

2. ## **Actual Prompt (attached this :** [https://drive.google.com/file/d/1fb9KK\_pH9fIXlaJFPlL9-mEG\_y0bDRr5/view?usp=sharing](https://drive.google.com/file/d/1fb9KK_pH9fIXlaJFPlL9-mEG_y0bDRr5/view?usp=sharing))

Now, I am giving you a list of 300 hsc level physics,chemistry,math mcq questions \= Q do the following:

set s

for each question q in Q:  
 set x \= extract\_skills(q)  
 for each skill sk in x:  
 s.insert({sk, q.subject})

for each {skill,subject} {sk,sub} in s:  
 "tuples.json".append({sk,sub})

tuples.json should look like this :  
 \[ {  
 "bloom": "Understand",  
 "skillId": "PHY\_MEAS1",  
 "skillFull": "Explain the nature of physical quantities.",  
 "topicKey": "PHY\_MEAS",  
 "topicLabel": "1.1 · Physical World and Measurement",  
 "subject": "Physics"  
 },  
 {  
 "bloom": "Apply",  
 "skillId": "PHY\_VEC3",  
 "skillFull": "Perform addition of vectors.",  
 "topicKey": "PHY\_VEC",  
 "topicLabel": "1.2 · Vectors",  
 "subject": "Physics"  
 }  
 \]  
 as there are 300 questions, it is expected that, some questions may target more than one skills, and some skills might be required in more than one questions. Now, give me the tuples.json.

