// ── PASTE THIS FIRST ──

const T = {
  EXT:{ label:'External Prerequisites',        bg:'#EAECEE', bd:'#717D7E', fg:'#424949' },
  T1: { label:'1 · Real Numbers',              bg:'#D6EAF8', bd:'#2E86C1', fg:'#1A5276' },
  T2: { label:'2 · HCF',                       bg:'#D5F5E3', bd:'#1E8449', fg:'#145A32' },
  T3: { label:'3 · LCM',                       bg:'#FDEBD0', bd:'#CA6F1E', fg:'#784212' },
  T4: { label:'4 · Percentage',                bg:'#FADBD8', bd:'#C0392B', fg:'#7B241C' },
  T5: { label:'5 · Simple & Compound Profit',  bg:'#E8DAEF', bd:'#7D3C98', fg:'#4A235A' },
  T6: { label:'6 · Ratio & Proportions',       bg:'#D1F2EB', bd:'#148F77', fg:'#0E6655' },
  T7: { label:'7 · Profit & Loss',             bg:'#FEF9E7', bd:'#B7950B', fg:'#7D6608' },
};

const ND = [
  // EXT
  {id:'PRE8', lbl:'PRE-8\nAlgebraic\nmanipulation',    full:'Basic algebraic manipulation — solve for a single variable',                                          tp:'EXT', sub:'External'},
  {id:'PRE9', lbl:'PRE-9\nSystems of\nequations',      full:'Set up and solve a system of two linear equations with two unknowns',                                  tp:'EXT', sub:'External'},
  // T1
  {id:'PRE1', lbl:'PRE-1\nWhole numbers',              full:'Identify and write whole numbers up to large values (lakhs/crores)',                                    tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE2', lbl:'PRE-2\nAdd & subtract',             full:'Add and subtract whole numbers',                                                                       tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE3', lbl:'PRE-3\nMultiply',                   full:'Multiply whole numbers',                                                                               tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE4', lbl:'PRE-4\nDivide',                     full:'Divide whole numbers (including remainders and non-integer results)',                                   tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE5', lbl:'PRE-5\nFractions ↔\ndecimals',     full:'Convert between fractions and decimals',                                                               tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE6', lbl:'PRE-6\nDecimal\narithmetic',        full:'Multiply and divide decimal numbers',                                                                  tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'LG2',  lbl:'LG-2\nExact\ndivisibility',         full:'Check exact divisibility of one number by another',                                                    tp:'T1',  sub:'1.2 Divisibility & Number Properties'},
  {id:'LG4',  lbl:'LG-4\nDivisibility\nrules 2,3,4,5,9',full:'Apply divisibility rules for 2, 3, 4, 5, and 9',                                                    tp:'T1',  sub:'1.2 Divisibility & Number Properties'},
  {id:'LG5',  lbl:'LG-5\nPrime or\ncomposite',         full:'Identify whether a number is prime or composite',                                                      tp:'T1',  sub:'1.2 Divisibility & Number Properties'},
  {id:'LG9',  lbl:'LG-9\nCo-prime\nnumbers',           full:'Identify whether two or more numbers are co-prime',                                                    tp:'T1',  sub:'1.2 Divisibility & Number Properties'},
  {id:'LG1',  lbl:'LG-1\nList\nmultiples',             full:'List multiples of a given number',                                                                     tp:'T1',  sub:'1.3 Factors, Multiples & Prime Factorization'},
  {id:'LG3',  lbl:'LG-3\nList all\nfactors',           full:'List all factors of a number by trial division',                                                       tp:'T1',  sub:'1.3 Factors, Multiples & Prime Factorization'},
  {id:'LG8',  lbl:'LG-8\nPrime\nfactorization',        full:'Express a number as a product of prime factors (factor tree or repeated division)',                     tp:'T1',  sub:'1.3 Factors, Multiples & Prime Factorization'},
  // T2
  {id:'LG7',  lbl:'LG-7\nCommon\nfactors',             full:'Find common factors of two numbers',                                                                   tp:'T2',  sub:'2.1 Common Factors'},
  {id:'LG10', lbl:'LG-10\nHCF by\nenumeration',        full:'Find HCF of two numbers by factor enumeration (list all factors, pick greatest common)',               tp:'T2',  sub:'2.2 Methods of Finding HCF'},
  {id:'LG11', lbl:'LG-11\nHCF by prime\nfactors',      full:'Find HCF of two numbers by common prime factors (prime factorize both, multiply common primes)',       tp:'T2',  sub:'2.2 Methods of Finding HCF'},
  {id:'LG12', lbl:'LG-12\nHCF by division\n(Euclidean)',full:'Find HCF of two numbers by division method (Euclidean algorithm)',                                    tp:'T2',  sub:'2.2 Methods of Finding HCF'},
  {id:'LG16', lbl:'LG-16\nHCF of\n3+ numbers',         full:'Find HCF of three or more numbers',                                                                    tp:'T2',  sub:'2.3 Extension & Applications'},
  {id:'LG18', lbl:'LG-18\nHCF\napplications',          full:'Apply HCF to equal-distribution problems (e.g., divide items into largest equal groups)',              tp:'T2',  sub:'2.3 Extension & Applications'},
  // T3
  {id:'LG6',  lbl:'LG-6\nCommon\nmultiples',           full:'Find common multiples of two numbers',                                                                 tp:'T3',  sub:'3.1 Common Multiples'},
  {id:'LG13', lbl:'LG-13\nLCM by listing\nmultiples',  full:'Find LCM of two numbers by listing and comparing multiples',                                           tp:'T3',  sub:'3.2 Methods of Finding LCM'},
  {id:'LG14', lbl:'LG-14\nLCM by prime\nfactorization',full:'Find LCM of two numbers by prime factorization (take highest power of each prime)',                    tp:'T3',  sub:'3.2 Methods of Finding LCM'},
  {id:'LG15', lbl:'LG-15\nLCM by\nladder method',      full:"Find LCM of two numbers by Euclid's ladder method (successive division by common/remaining primes)",   tp:'T3',  sub:'3.2 Methods of Finding LCM'},
  {id:'LG17', lbl:'LG-17\nLCM of\n3+ numbers',         full:'Find LCM of three or more numbers',                                                                    tp:'T3',  sub:'3.3 Extension'},
  {id:'LG19', lbl:'LG-19\nLCM scheduling\napplications',full:'Apply LCM to scheduling and synchronization problems (e.g., when two periodic events next coincide)', tp:'T3',  sub:'3.4 Applications & Relationships'},
  {id:'LG20', lbl:'LG-20\nProduct =\nHCF × LCM',       full:'Use the relationship: Product of two numbers = HCF × LCM',                                             tp:'T3',  sub:'3.4 Applications & Relationships'},
  {id:'LG22', lbl:'LG-22\nFind unknown\nvia HCF & LCM',full:'Find an unknown number given the other number, the HCF, and the LCM, using the product relationship',  tp:'T3',  sub:'3.4 Applications & Relationships'},
  {id:'LG21', lbl:'LG-21\nHCF & LCM\nof fractions',    full:'Find HCF and LCM of fractions: HCF=(HCF of numerators)/(LCM of denominators); LCM=(LCM of numerators)/(HCF of denominators)', tp:'T3', sub:'3.5 HCF & LCM of Fractions & Decimals'},
  {id:'LG23', lbl:'LG-23\nHCF & LCM\nof decimals',     full:'Find HCF and LCM of decimal fractions (equalize decimal places, treat as integers, reposition decimal point)', tp:'T3', sub:'3.5 HCF & LCM of Fractions & Decimals'},
  // T4
  {id:'PC1',  lbl:'PC-1\nDefine\npercentage',           full:'Define percentage as parts per hundred',                                                               tp:'T4',  sub:'4.1 Concept & Definition'},
  {id:'PC2',  lbl:'PC-2\nFraction → %',                 full:'Express a fraction as a percentage',                                                                  tp:'T4',  sub:'4.2 Conversions'},
  {id:'PC3',  lbl:'PC-3\n% → fraction',                 full:'Express a percentage as a fraction',                                                                  tp:'T4',  sub:'4.2 Conversions'},
  {id:'PC4',  lbl:'PC-4\nDecimal → %',                  full:'Express a decimal as a percentage',                                                                   tp:'T4',  sub:'4.2 Conversions'},
  {id:'PC5',  lbl:'PC-5\n% → decimal',                  full:'Express a percentage as a decimal',                                                                   tp:'T4',  sub:'4.2 Conversions'},
  {id:'PC6',  lbl:'PC-6\nConvert all\nforms',            full:'Convert fluently between ratio, fraction, decimal, and percentage',                                   tp:'T4',  sub:'4.2 Conversions'},
  {id:'PCA1', lbl:'PCA-1\nCalculate\nx% of qty',         full:'Calculate a percentage of a given quantity',                                                          tp:'T4',  sub:'4.3 Percentage Calculations'},
  {id:'PCA2', lbl:'PCA-2\nQty as %\nof another',         full:'Express one quantity as a percentage of another',                                                     tp:'T4',  sub:'4.3 Percentage Calculations'},
  {id:'PCA3', lbl:'PCA-3\nFind original\nvalue from %',  full:'Find the original value given a percentage of it',                                                    tp:'T4',  sub:'4.3 Percentage Calculations'},
  {id:'PCA4', lbl:'PCA-4\n% increase',                   full:'Calculate percentage increase',                                                                       tp:'T4',  sub:'4.4 Percentage Change'},
  {id:'PCA5', lbl:'PCA-5\n% decrease',                   full:'Calculate percentage decrease',                                                                       tp:'T4',  sub:'4.4 Percentage Change'},
  {id:'PCA6', lbl:'PCA-6\n% change',                     full:'Calculate percentage change (increase or decrease) between two values',                               tp:'T4',  sub:'4.4 Percentage Change'},
  // T5
  {id:'SI1',  lbl:'SI-1\nIdentify P',                   full:'Identify and label the principal (P) in a word problem',                                              tp:'T5',  sub:'5.1.1 Identifying Variables'},
  {id:'SI2',  lbl:'SI-2\nIdentify R',                   full:'Identify and label the rate of profit/interest (R) in a word problem',                                tp:'T5',  sub:'5.1.1 Identifying Variables'},
  {id:'SI3',  lbl:'SI-3\nIdentify T',                   full:'Identify and label the time period (T) in a word problem',                                            tp:'T5',  sub:'5.1.1 Identifying Variables'},
  {id:'SI4',  lbl:'SI-4\nFormula\nSI = PRT/100',        full:'State the simple profit formula: SI = PRT/100',                                                       tp:'T5',  sub:'5.1.2 Core Formula'},
  {id:'SI5',  lbl:'SI-5\nCompute SI',                   full:'Substitute known values into SI = PRT/100 and compute the result',                                    tp:'T5',  sub:'5.1.2 Core Formula'},
  {id:'SI6',  lbl:'SI-6\nTotal amount\nA = P + SI',     full:'Calculate total amount under simple profit: A = P + SI',                                              tp:'T5',  sub:'5.1.2 Core Formula'},
  {id:'SI7',  lbl:'SI-7\nIsolate P',                    full:'Isolate P given SI, R, and T (rearrange formula)',                                                    tp:'T5',  sub:'5.1.3 Rearranging Formula'},
  {id:'SI8',  lbl:'SI-8\nIsolate R',                    full:'Isolate R given SI, P, and T (rearrange formula)',                                                    tp:'T5',  sub:'5.1.3 Rearranging Formula'},
  {id:'SI9',  lbl:'SI-9\nIsolate T',                    full:'Isolate T given SI, P, and R (rearrange formula)',                                                    tp:'T5',  sub:'5.1.3 Rearranging Formula'},
  {id:'SI10', lbl:'SI-10\nMulti-step\nword problems',   full:'Solve multi-step word problems combining SI formula with one unknown',                                 tp:'T5',  sub:'5.1.4 Advanced Simple Profit'},
  {id:'SI11', lbl:'SI-11\nFractional\nrate or time',    full:'Calculate SI when rate or time is given as a fraction (e.g., 2.5 years, 7.5%)',                       tp:'T5',  sub:'5.1.4 Advanced Simple Profit'},
  {id:'SI12', lbl:'SI-12\nSI for part\nof a year',      full:'Calculate SI for part of a year (e.g., 9 months = 9/12 years)',                                       tp:'T5',  sub:'5.1.4 Advanced Simple Profit'},
  {id:'SI13', lbl:'SI-13\nFind P for\ntarget SI',       full:'Determine the principal required to earn a given SI at given R and T',                                 tp:'T5',  sub:'5.1.4 Advanced Simple Profit'},
  {id:'SI14', lbl:'SI-14\nCompare\nSI schemes',         full:'Compare two simple profit schemes and identify the better one',                                        tp:'T5',  sub:'5.1.4 Advanced Simple Profit'},
  {id:'CI1',  lbl:'CI-1\nUnderstand\ncompounding',      full:"Understand how interest compounds: each period's profit is added to the principal",                   tp:'T5',  sub:'5.2.1 Compound Concept'},
  {id:'CI2',  lbl:'CI-2\nManual CI\nyear-by-year',      full:'Compute CI manually year-by-year for T = 2 and T = 3',                                                tp:'T5',  sub:'5.2.1 Compound Concept'},
  {id:'CI3',  lbl:'CI-3\nFormula\nA=P(1+R/100)^T',     full:'State the annual compounding formula: A = P(1 + R/100)^T',                                            tp:'T5',  sub:'5.2.2 Annual Compounding Formula'},
  {id:'CI4',  lbl:'CI-4\nEvaluate\n(1+R/100)^T',       full:'Evaluate (1 + R/100)^T for integer T using repeated multiplication',                                  tp:'T5',  sub:'5.2.2 Annual Compounding Formula'},
  {id:'CI5',  lbl:'CI-5\nCompute A & CI\n(annual)',     full:'Compute A and CI using A = P(1 + R/100)^T for annual compounding',                                    tp:'T5',  sub:'5.2.2 Annual Compounding Formula'},
  {id:'CI6',  lbl:'CI-6\nCompounding\nperiod',          full:'Identify the compounding period (annual, half-yearly, quarterly)',                                     tp:'T5',  sub:'5.2.3 Compounding Periods'},
  {id:'CI7',  lbl:'CI-7\nAdjust for\nhalf-yearly',      full:'Adjust rate and time for half-yearly compounding (R→R/2, T→2T)',                                      tp:'T5',  sub:'5.2.3 Compounding Periods'},
  {id:'CI8',  lbl:'CI-8\nAdjust for\nquarterly',        full:'Adjust rate and time for quarterly compounding (R→R/4, T→4T)',                                        tp:'T5',  sub:'5.2.3 Compounding Periods'},
  {id:'CI9',  lbl:'CI-9\nCI half-yearly\n& quarterly',  full:'Compute A and CI for half-yearly and quarterly compounding periods',                                   tp:'T5',  sub:'5.2.3 Compounding Periods'},
  {id:'CI10', lbl:'CI-10\nFind P\nfrom CI',             full:'Find original principal P given A, R, and T under CI',                                                 tp:'T5',  sub:'5.2.4 Reverse & Comparison'},
  {id:'CI11', lbl:'CI-11\nFind R\nfrom CI',             full:'Find rate R given P, A, and T under CI (integer T = 2)',                                               tp:'T5',  sub:'5.2.4 Reverse & Comparison'},
  {id:'CI12', lbl:'CI-12\nFind T\nfrom CI',             full:'Find T given P, A, and R under CI by trial or pattern (small integer T)',                              tp:'T5',  sub:'5.2.4 Reverse & Comparison'},
  {id:'CI13', lbl:'CI-13\nCI(T=1)\nequals SI',          full:'Compute CI for T = 1 and verify it equals SI for the same values',                                    tp:'T5',  sub:'5.2.4 Reverse & Comparison'},
  {id:'CI14', lbl:'CI-14\nCompare CI\nand SI',          full:'Compare CI and SI for same P, R, T and explain the difference',                                        tp:'T5',  sub:'5.2.4 Reverse & Comparison'},
  {id:'CI15', lbl:'CI-15\nCI−SI =\nP(R/100)²',         full:'Calculate the difference CI − SI = P(R/100)² for T = 2',                                              tp:'T5',  sub:'5.2.4 Reverse & Comparison'},
  {id:'CI16', lbl:'CI-16\nReal-world CI\napplications', full:'Apply CI to real-world contexts: population growth, depreciation, investment',                         tp:'T5',  sub:'5.2.5 Real-World Applications'},
  {id:'CI17', lbl:'CI-17\nCI word\nproblems',           full:'Solve two-step word problems requiring CI computation and comparison',                                  tp:'T5',  sub:'5.2.5 Real-World Applications'},
  // T6
  {id:'RF1',  lbl:'RF-1\nDefine ratio',                 full:'Define ratio as a comparison of two quantities of the same kind and unit by division',                 tp:'T6',  sub:'6.1.1 Ratio Concept & Notation'},
  {id:'RF2',  lbl:'RF-2\nAntecedent &\nconsequent',     full:'Identify antecedent and consequent in a ratio',                                                       tp:'T6',  sub:'6.1.1 Ratio Concept & Notation'},
  {id:'RF3',  lbl:'RF-3\nRatio as\nfraction',           full:'Express a ratio as a fraction and vice versa',                                                        tp:'T6',  sub:'6.1.1 Ratio Concept & Notation'},
  {id:'RF4',  lbl:'RF-4\nCommon\nunit',                 full:'Convert quantities to a common unit before forming a ratio',                                           tp:'T6',  sub:'6.1.1 Ratio Concept & Notation'},
  {id:'RF5',  lbl:'RF-5\nEquivalent\nratios',           full:'Find equivalent ratios',                                                                              tp:'T6',  sub:'6.1.2 Operations on Ratios'},
  {id:'RF6',  lbl:'RF-6\nSimplify ratio\nusing HCF',    full:'Simplify a ratio to lowest terms using HCF',                                                          tp:'T6',  sub:'6.1.2 Operations on Ratios'},
  {id:'RF7',  lbl:'RF-7\nCompare by\nratio',            full:'Compare two quantities using ratio',                                                                  tp:'T6',  sub:'6.1.2 Operations on Ratios'},
  {id:'RF8',  lbl:'RF-8\nTypes of\nratio',              full:'Distinguish between ratio of less inequality, greater inequality, and unit ratio',                     tp:'T6',  sub:'6.1.3 Types of Ratio'},
  {id:'RF9',  lbl:'RF-9\nInverse\nratio',               full:'Form the inverse ratio by interchanging antecedent and consequent',                                   tp:'T6',  sub:'6.1.3 Types of Ratio'},
  {id:'RF10', lbl:'RF-10\nCompound\nratio',             full:'Calculate the compound (mixed) ratio of two or more simple ratios',                                   tp:'T6',  sub:'6.1.3 Types of Ratio'},
  {id:'RF11', lbl:'RF-11\nDivide qty\nin ratio',        full:'Divide a quantity in a given ratio',                                                                  tp:'T6',  sub:'6.1.4 Ratio Application'},
  {id:'PF1',  lbl:'PF-1\nDefine\nproportion',           full:'Define proportion as the equality of two ratios (a:b = c:d)',                                         tp:'T6',  sub:'6.2.1 Proportion Concept'},
  {id:'PF2',  lbl:'PF-2\nMeans &\nextremes',            full:'Identify the four terms of a proportion and distinguish means from extremes',                         tp:'T6',  sub:'6.2.1 Proportion Concept'},
  {id:'PF3',  lbl:'PF-3\nCross-\nmultiplication',       full:'Apply the cross-multiplication property (product of means = product of extremes)',                     tp:'T6',  sub:'6.2.2 Proportion Properties'},
  {id:'PF4',  lbl:'PF-4\nVerify\nproportion',           full:'Determine if four numbers are in proportion',                                                         tp:'T6',  sub:'6.2.2 Proportion Properties'},
  {id:'PF5',  lbl:'PF-5\nMissing 4th\nterm',            full:'Find the missing fourth term in a proportion',                                                        tp:'T6',  sub:'6.2.2 Proportion Properties'},
  {id:'PF6',  lbl:'PF-6\nContinued\nproportion',        full:'Define and identify continued proportion (a:b = b:c, so b² = ac)',                                    tp:'T6',  sub:'6.2.3 Continued Proportion'},
  {id:'PF7',  lbl:'PF-7\nMean & third\nproportional',   full:'Calculate the mean proportional and third proportional in a continued proportion',                    tp:'T6',  sub:'6.2.3 Continued Proportion'},
  {id:'TP1',  lbl:'TP-1\nDefine direct\nproportion',    full:'Define direct proportion',                                                                            tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP2',  lbl:'TP-2\nIdentify direct\nproportion',  full:'Identify if two quantities are in direct proportion',                                                 tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP3',  lbl:'TP-3\nSolve direct\nproportion',     full:'Solve problems using direct proportion',                                                              tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP4',  lbl:'TP-4\nDefine inverse\nproportion',   full:'Define inverse proportion',                                                                           tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP5',  lbl:'TP-5\nIdentify inverse\nproportion', full:'Identify if two quantities are in inverse proportion',                                                tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP6',  lbl:'TP-6\nSolve inverse\nproportion',    full:'Solve problems using inverse proportion',                                                             tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'AT1',  lbl:'AT-1\nInvertendo',                   full:'Apply Invertendo: if a:b = c:d, then b:a = d:c',                                                      tp:'T6',  sub:'6.4 Algebraic Transformations'},
  {id:'AT2',  lbl:'AT-2\nAlternendo',                   full:'Apply Alternendo: if a:b = c:d, then a:c = b:d',                                                      tp:'T6',  sub:'6.4 Algebraic Transformations'},
  {id:'AT3',  lbl:'AT-3\nComponendo',                   full:'Apply Componendo: if a/b = c/d, then (a+b)/b = (c+d)/d',                                              tp:'T6',  sub:'6.4 Algebraic Transformations'},
  {id:'AT4',  lbl:'AT-4\nDividendo',                    full:'Apply Dividendo: if a/b = c/d, then (a-b)/b = (c-d)/d',                                               tp:'T6',  sub:'6.4 Algebraic Transformations'},
  {id:'AT5',  lbl:'AT-5\nComponendo-\nDividendo',       full:'Apply Componendo-Dividendo: if a/b = c/d, then (a+b)/(a-b) = (c+d)/(c-d)',                            tp:'T6',  sub:'6.4 Algebraic Transformations'},
  // T7
  {id:'PL1',  lbl:'PL-1\nIdentify CP',                  full:'Identify Cost Price (CP) in a word problem, including overhead costs (rent, transport, etc.)',         tp:'T7',  sub:'7.1 Core Concepts'},
  {id:'PL2',  lbl:'PL-2\nIdentify SP',                  full:'Identify Selling Price (SP) in a word problem',                                                       tp:'T7',  sub:'7.1 Core Concepts'},
  {id:'PL3',  lbl:'PL-3\nProfit or\nloss?',             full:'Determine whether a transaction results in profit, loss, or no profit/loss by comparing CP and SP',   tp:'T7',  sub:'7.1 Core Concepts'},
  {id:'PL4',  lbl:'PL-4\nProfit / loss\namount',        full:'Calculate profit or loss amount (Profit = SP − CP; Loss = CP − SP)',                                   tp:'T7',  sub:'7.1 Core Concepts'},
  {id:'PL5',  lbl:'PL-5\nProfit / loss\n% on CP',       full:'Calculate profit or loss percentage on CP',                                                           tp:'T7',  sub:'7.2 Percentage Calculations'},
  {id:'PL6',  lbl:'PL-6\nFind SP\nfrom %',              full:'Calculate SP given CP and a profit or loss percentage',                                                tp:'T7',  sub:'7.2 Percentage Calculations'},
  {id:'PL7',  lbl:'PL-7\nFind CP\nfrom %',              full:'Calculate CP given SP and a profit or loss percentage',                                                tp:'T7',  sub:'7.2 Percentage Calculations'},
  {id:'PL8',  lbl:'PL-8\nUnit price\nfrom bulk',        full:'Calculate CP or SP per unit from a bulk rate',                                                        tp:'T7',  sub:'7.3 Unit-Rate Problems'},
  {id:'PL9',  lbl:'PL-9\nOverall %\n(unit-rate)',       full:'Calculate overall profit% or loss% when buying and selling are both expressed in unit-rate form',      tp:'T7',  sub:'7.3 Unit-Rate Problems'},
  {id:'PL10', lbl:'PL-10\nTarget\nselling rate',        full:'Determine the required selling rate (items per taka) to achieve a target profit%',                     tp:'T7',  sub:'7.3 Unit-Rate Problems'},
  {id:'PL11', lbl:'PL-11\nCP: two SP\nscenarios',       full:'Find CP when two different SP scenarios and their difference in value are given',                      tp:'T7',  sub:'7.4 Multi-Condition & Reverse'},
  {id:'PL12', lbl:'PL-12\nCP from\nproportional parts', full:'Find CP when SP and total amount are both expressed as proportional parts',                            tp:'T7',  sub:'7.4 Multi-Condition & Reverse'},
  {id:'PL13', lbl:'PL-13\nCP via chain\nof profit %',   full:'Find original CP through a chain of successive profit percentages (e.g., wholesaler → retailer)',     tp:'T7',  sub:'7.4 Multi-Condition & Reverse'},
  {id:'PL14', lbl:'PL-14\nVAT\nproblems',               full:'Solve VAT problems: find original CP given SP inclusive of VAT, or calculate VAT payable given SP and VAT rate', tp:'T7', sub:'7.4 Multi-Condition & Reverse'},
  {id:'PL15', lbl:'PL-15\nTwo buy rates\nuniform sell',  full:'Solve problems where items are bought at two different rates and sold at a uniform rate',              tp:'T7',  sub:'7.5 Advanced Composite'},
  {id:'PL16', lbl:'PL-16\nCP with\nprincipal & time',   full:'Find CP and profit% when profit, principal fraction, and time are given together',                     tp:'T7',  sub:'7.5 Advanced Composite'},
  {id:'PL17', lbl:'PL-17\nMulti-part\ncomposite',       full:'Solve multi-part problems combining percentage, profit/loss, and algebraic equation-setting',          tp:'T7',  sub:'7.5 Advanced Composite'},
];

const CROSS_TOPIC = {
  'LG8':  ['T2', 'T3'],
  'LG12': ['T2', 'T3'],
  'LG16': ['T2', 'T3'],
  'LG20': ['T2', 'T3'],
  'LG21': ['T2', 'T3'],
  'LG11': ['T2', 'T6'],
  'PC1':  ['T4', 'T5'],
  'PCA1': ['T4', 'T5', 'T7'],
  'PCA2': ['T4', 'T7'],
  'PCA3': ['T4', 'T7'],
  'PC6':  ['T4', 'T7'],
  'SI5':  ['T5', 'T7'],
  'PL5':  ['T4', 'T7'],
  'PL6':  ['T4', 'T7'],
  'PL7':  ['T4', 'T7'],
};


const BLOOM_LEVELS = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'];

const skillTopics = {};
ND.forEach(n => { skillTopics[n.id] = new Set([n.tp]); });
Object.entries(CROSS_TOPIC).forEach(([skillId, topics]) => {
  topics.forEach(tp => skillTopics[skillId].add(tp));
});

const tuples = [];
ND.forEach(skill => {
  const topicSet = skillTopics[skill.id];
  topicSet.forEach(topicKey => {
    if (topicKey === 'EXT') return; // skip external prerequisites as topics
    BLOOM_LEVELS.forEach(bloom => {
      tuples.push({
        bloom,
        skillId: skill.id,
        skillFull: skill.full,
        topicKey,
        topicLabel: T[topicKey].label
      });
    });
  });
});

console.log(`Total tuples: ${tuples.length}`);
console.log(JSON.stringify(tuples, null, 2));

const fs = require('fs');
fs.writeFileSync('tuples.json', JSON.stringify(tuples, null, 2));
console.log(`Saved ${tuples.length} tuples to tuples.json`);