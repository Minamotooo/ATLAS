/*
 * One real item from the ATLAS question bank (questions.id 15346, skill
 * CHE_GASLAWS5, "Apply the ideal gas law"), shown on the landing page exactly
 * as the practice page would render it. The wrong options are tagged in the
 * database with MAT2_POLYNOMIAL7, a Higher Mathematics skill: the chemistry
 * mistake traces back to rearranging a formula.
 */
export const SAMPLE_QUESTION = {
  id: 15346,
  subject: 'Chemistry',
  stem: String.raw`$27 ^\circ\text{C}$ তাপমাত্রায় এবং $1.5\text{ atm}$ চাপে $2\text{ g}$ হাইড্রোজেন গ্যাসের আয়তন কত হবে?`,
  options: [
    {
      label: 'A',
      text: String.raw`$8.21\text{ L}$`,
      correct: false,
      explanation: String.raw`এখানে মোলের সংখ্যা গণনায় ভুল করা হয়েছে (যেমন মোল সংখ্যা $n=2$ ধরা হয়েছে, যেখানে $n = 2/2 = 1\text{ mol}$)। সঠিক সূত্র $PV = nRT$ ব্যবহার করলে সঠিক মান পাওয়া যায়।`,
    },
    {
      label: 'B',
      text: String.raw`$16.42\text{ L}$`,
      correct: true,
      explanation: String.raw`দেওয়া আছে, চাপ $P = 1.5\text{ atm}$, ভর $w = 2\text{ g}$, মোলার ভর $M = 2\text{ g/mol}$, তাপমাত্রা $T = 27 + 273 = 300\text{ K}$, সার্বজনীন গ্যাস ধ্রুবক $R =0.0821\text{ L atm K}^{-1}\text{mol}^{-1}$। আদর্শ গ্যাস সমীকরণ হতে, $V = \frac{nRT}{P} = \frac{(2/2) \times 0.0821 \times 300}{1.5} = 16.42\text{ L}$।`,
    },
    {
      label: 'C',
      text: String.raw`$24.63\text{ L}$`,
      correct: false,
      explanation: 'তাপমাত্রাকে কেলভিনে রূপান্তর না করে সেলসিয়াসে হিসাব করার কারণে এই ভুল মানটি এসেছে।',
    },
    {
      label: 'D',
      text: String.raw`$4.10\text{ L}$`,
      correct: false,
      explanation: 'চাপের মান দিয়ে ভাগ করার সময় গাণিতিক ভুল বা উলটো ভগ্নাংশ ব্যবহারের ফলে এই মান এসেছে।',
    },
  ],
  // option_missing_prerequisites for every wrong option
  missingSkill: {
    id: 'MAT2_POLYNOMIAL7',
    subject: 'Mathematics',
    en: 'Rearrange a multi-variable formula to make a stated variable its subject.',
    bn: 'বহু-চলকের সূত্রকে সাজিয়ে নির্দিষ্ট চলককে বিষয় (subject) করা।',
  },
};
