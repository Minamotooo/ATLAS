// ─────────────────────────────────────────────
// NODE DATA
// ─────────────────────────────────────────────
const ND = [
  // EXT
  {id:'PRE8', lbl:'PRE-8\nAlgebraic\nmanipulation',    full:'Basic algebraic manipulation — solve for a single variable',                                          tp:'EXT', sub:'External'},
  {id:'PRE9', lbl:'PRE-9\nSystems of\nequations',      full:'Set up and solve a system of two linear equations with two unknowns',                                  tp:'EXT', sub:'External'},
  // T1 — 1.1
  {id:'PRE1', lbl:'PRE-1\nWhole numbers',              full:'Identify and write whole numbers up to large values (lakhs/crores)',                                    tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE2', lbl:'PRE-2\nAdd & subtract',             full:'Add and subtract whole numbers',                                                                       tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE3', lbl:'PRE-3\nMultiply',                   full:'Multiply whole numbers',                                                                               tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE4', lbl:'PRE-4\nDivide',                     full:'Divide whole numbers (including remainders and non-integer results)',                                   tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE5', lbl:'PRE-5\nFractions ↔\ndecimals',     full:'Convert between fractions and decimals',                                                               tp:'T1',  sub:'1.1 Number Sense & Operations'},
  {id:'PRE6', lbl:'PRE-6\nDecimal\narithmetic',        full:'Multiply and divide decimal numbers',                                                                  tp:'T1',  sub:'1.1 Number Sense & Operations'},
  // T1 — 1.2
  {id:'LG2',  lbl:'LG-2\nExact\ndivisibility',         full:'Check exact divisibility of one number by another',                                                    tp:'T1',  sub:'1.2 Divisibility & Number Properties'},
  {id:'LG4',  lbl:'LG-4\nDivisibility\nrules 2,3,4,5,9',full:'Apply divisibility rules for 2, 3, 4, 5, and 9',                                                    tp:'T1',  sub:'1.2 Divisibility & Number Properties'},
  {id:'LG5',  lbl:'LG-5\nPrime or\ncomposite',         full:'Identify whether a number is prime or composite',                                                      tp:'T1',  sub:'1.2 Divisibility & Number Properties'},
  {id:'LG9',  lbl:'LG-9\nCo-prime\nnumbers',           full:'Identify whether two or more numbers are co-prime',                                                    tp:'T1',  sub:'1.2 Divisibility & Number Properties'},
  // T1 — 1.3
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
  // T5 SI
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
  // T5 CI
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
  // T6 Ratio
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
  // T6 Proportion
  {id:'PF1',  lbl:'PF-1\nDefine\nproportion',           full:'Define proportion as the equality of two ratios (a:b = c:d)',                                         tp:'T6',  sub:'6.2.1 Proportion Concept'},
  {id:'PF2',  lbl:'PF-2\nMeans &\nextremes',            full:'Identify the four terms of a proportion and distinguish means from extremes',                         tp:'T6',  sub:'6.2.1 Proportion Concept'},
  {id:'PF3',  lbl:'PF-3\nCross-\nmultiplication',       full:'Apply the cross-multiplication property (product of means = product of extremes)',                     tp:'T6',  sub:'6.2.2 Proportion Properties'},
  {id:'PF4',  lbl:'PF-4\nVerify\nproportion',           full:'Determine if four numbers are in proportion',                                                         tp:'T6',  sub:'6.2.2 Proportion Properties'},
  {id:'PF5',  lbl:'PF-5\nMissing 4th\nterm',            full:'Find the missing fourth term in a proportion',                                                        tp:'T6',  sub:'6.2.2 Proportion Properties'},
  {id:'PF6',  lbl:'PF-6\nContinued\nproportion',        full:'Define and identify continued proportion (a:b = b:c, so b² = ac)',                                    tp:'T6',  sub:'6.2.3 Continued Proportion'},
  {id:'PF7',  lbl:'PF-7\nMean & third\nproportional',   full:'Calculate the mean proportional and third proportional in a continued proportion',                    tp:'T6',  sub:'6.2.3 Continued Proportion'},
  // T6 Types
  {id:'TP1',  lbl:'TP-1\nDefine direct\nproportion',    full:'Define direct proportion',                                                                            tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP2',  lbl:'TP-2\nIdentify direct\nproportion',  full:'Identify if two quantities are in direct proportion',                                                 tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP3',  lbl:'TP-3\nSolve direct\nproportion',     full:'Solve problems using direct proportion',                                                              tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP4',  lbl:'TP-4\nDefine inverse\nproportion',   full:'Define inverse proportion',                                                                           tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP5',  lbl:'TP-5\nIdentify inverse\nproportion', full:'Identify if two quantities are in inverse proportion',                                                tp:'T6',  sub:'6.3 Types of Proportion'},
  {id:'TP6',  lbl:'TP-6\nSolve inverse\nproportion',    full:'Solve problems using inverse proportion',                                                             tp:'T6',  sub:'6.3 Types of Proportion'},
  // T6 Algebraic
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

// ─────────────────────────────────────────────
// EDGE DATA
// ─────────────────────────────────────────────
const ED = [
  // T1
  ['PRE3','PRE5'],['PRE4','PRE5'],['PRE5','PRE6'],
  ['PRE4','LG2'],['LG2','LG4'],['LG2','LG5'],['LG3','LG5'],['LG5','LG9'],
  ['PRE3','LG1'],['PRE4','LG3'],['LG5','LG8'],['LG3','LG8'],
  // T2
  ['LG3','LG7'],['LG7','LG10'],['LG8','LG11'],['LG7','LG11'],
  ['PRE4','LG12'],['LG2','LG12'],
  ['LG10','LG16'],['LG11','LG16'],['LG12','LG16'],
  ['LG16','LG18'],
  // T3
  ['LG1','LG6'],['LG6','LG13'],['LG8','LG14'],['LG12','LG15'],
  ['LG13','LG17'],['LG14','LG17'],['LG15','LG17'],
  ['LG17','LG19'],
  ['LG16','LG20'],['LG17','LG20'],['LG20','LG22'],
  ['LG16','LG21'],['LG17','LG21'],['PRE5','LG21'],
  ['LG21','LG23'],['PRE6','LG23'],
  // T4
  ['PRE4','PC1'],
  ['PC1','PC2'],['PRE5','PC2'],
  ['PC1','PC3'],
  ['PC1','PC4'],['PRE5','PC4'],
  ['PC1','PC5'],
  ['PC2','PC6'],['PC3','PC6'],['PC4','PC6'],['PC5','PC6'],
  ['PC1','PCA1'],['PRE3','PCA1'],
  ['PC1','PCA2'],['PRE4','PCA2'],
  ['PCA1','PCA3'],
  ['PCA2','PCA4'],['PCA2','PCA5'],
  ['PCA4','PCA6'],['PCA5','PCA6'],
  // T5 SI
  ['PRE1','SI1'],['PC1','SI2'],['PRE1','SI3'],
  ['SI1','SI4'],['SI2','SI4'],['SI3','SI4'],
  ['SI4','SI5'],['PRE3','SI5'],
  ['SI5','SI6'],['PRE2','SI6'],
  ['SI5','SI7'],['PRE8','SI7'],
  ['SI5','SI8'],['PRE8','SI8'],
  ['SI5','SI9'],['PRE8','SI9'],
  ['SI6','SI10'],['SI7','SI10'],['SI8','SI10'],['SI9','SI10'],
  ['SI5','SI11'],['PRE5','SI11'],
  ['SI5','SI12'],['PRE5','SI12'],
  ['SI7','SI13'],
  ['SI5','SI14'],
  // T5 CI
  ['SI6','CI1'],
  ['CI1','CI2'],['PCA1','CI2'],
  ['CI1','CI3'],
  ['CI3','CI4'],['PRE3','CI4'],
  ['CI4','CI5'],
  ['CI1','CI6'],
  ['CI6','CI7'],['CI6','CI8'],
  ['CI5','CI9'],['CI7','CI9'],['CI8','CI9'],
  ['CI5','CI10'],['PRE8','CI10'],
  ['CI5','CI11'],['PRE8','CI11'],
  ['CI5','CI12'],
  ['SI5','CI13'],['CI5','CI13'],
  ['CI13','CI14'],['CI14','CI15'],
  ['CI9','CI16'],
  ['CI9','CI17'],['CI14','CI17'],
  // T6 Ratio
  ['PRE4','RF1'],
  ['RF1','RF2'],
  ['RF1','RF3'],['PRE5','RF3'],
  ['PRE1','RF4'],
  ['RF1','RF5'],['PRE3','RF5'],
  ['RF1','RF6'],['LG11','RF6'],
  ['RF3','RF7'],
  ['RF7','RF8'],
  ['RF2','RF9'],
  ['RF1','RF10'],['PRE3','RF10'],
  ['RF6','RF11'],['PRE3','RF11'],
  // T6 Proportion
  ['RF1','PF1'],
  ['PF1','PF2'],['RF2','PF2'],
  ['PF2','PF3'],['PRE3','PF3'],
  ['PF3','PF4'],['PF3','PF5'],
  ['PF1','PF6'],['RF3','PF6'],
  ['PF6','PF7'],
  // T6 Types of Proportion
  ['PF1','TP1'],
  ['TP1','TP2'],['RF7','TP2'],
  ['TP2','TP3'],
  ['PF1','TP4'],
  ['TP4','TP5'],['RF7','TP5'],
  ['TP5','TP6'],
  // T6 Algebraic
  ['PF3','AT1'],['PF3','AT2'],['PF3','AT3'],['PF3','AT4'],
  ['AT3','AT5'],['AT4','AT5'],
  // T7
  ['PRE1','PL1'],['PRE1','PL2'],
  ['PL1','PL3'],['PL2','PL3'],
  ['PL3','PL4'],['PRE2','PL4'],
  ['PL4','PL5'],['PCA2','PL5'],
  ['PL5','PL6'],['PCA1','PL6'],
  ['PL5','PL7'],['PCA1','PL7'],['PRE8','PL7'],
  ['PL1','PL8'],['PL2','PL8'],['PRE4','PL8'],
  ['PL8','PL9'],['PL5','PL9'],
  ['PL9','PL10'],
  ['PL7','PL11'],['PRE8','PL11'],
  ['PL7','PL12'],
  ['PL7','PL13'],['PL5','PL13'],
  ['PL5','PL14'],['PC6','PL14'],
  ['PL9','PL15'],
  ['PL7','PL16'],['SI5','PL16'],
  ['PL15','PL17'],['PL16','PL17'],['PL11','PL17'],
  // ── NEW: PRE8 (algebraic manipulation) missing connections ──
  ['PRE8','PF5'],   // find missing 4th proportional — needs algebraic rearrangement
  ['PRE8','PF7'],   // mean & 3rd proportional — involves algebraic steps
  ['PRE8','SI13'],  // find P for target SI — isolating a variable
  ['PRE8','PCA3'],  // find original value from % — reverse percentage requires algebra
  ['PRE8','LG22'],  // find unknown via HCF×LCM product relationship — algebraic solve
  ['PRE8','AT1'],   // Invertendo — algebraic proof/application
  ['PRE8','AT2'],   // Alternendo — algebraic proof/application
  ['PRE8','AT3'],   // Componendo — algebraic proof/application
  ['PRE8','AT4'],   // Dividendo — algebraic proof/application
  ['PRE8','TP3'],   // solve direct proportion problems — needs to isolate variable
  ['PRE8','TP6'],   // solve inverse proportion problems — needs to isolate variable
  ['PRE8','PL16'],  // find CP/profit% with principal & time — algebraic rearrangement
  // ── NEW: PRE9 (systems of equations) connections ──
  ['PRE9','PL11'],  // find CP from two SP scenarios — sets up two equations, two unknowns
  ['PRE9','PL17'],  // multi-part composite P&L + algebra — can require simultaneous equations
];




const nodeMap = {};
ND.forEach(n => { nodeMap[n.id] = n; });


// Build adjacency: incoming edges
const inEdges = {}; // skillId → [prerequisite skillIds]
ED.forEach(([src, tgt]) => {
  if (!inEdges[tgt]) inEdges[tgt] = [];
  inEdges[tgt].push(src);
});

// Get all ancestors (direct prerequisites first, then transitive)
function getPrerequisites(skillId, depth = 0, visited = new Set()) {
  if (visited.has(skillId) || depth > 6) return [];
  visited.add(skillId);
  const directPrereqs = inEdges[skillId] || [];
  const result = directPrereqs.map(prereqId => ({
    id: prereqId,
    full: nodeMap[prereqId]?.full || prereqId,
    depth
  }));
  directPrereqs.forEach(prereqId => {
    result.push(...getPrerequisites(prereqId, depth + 1, visited));
  });
  return result;
}

const fs = require('fs');
const prereqs = {};
ND.forEach(skill => {
  prereqs[skill.id] = getPrerequisites(skill.id);
});
fs.writeFileSync('prereqs.json', JSON.stringify(prereqs, null, 2));
console.log('Saved prereqs.json');