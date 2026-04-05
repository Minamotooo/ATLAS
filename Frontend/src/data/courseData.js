export const coursesData = {
  en: [
    {
      id: 'class3-math',
      title: 'Class 3 Mathematics NCTB',
      code: 'CLASS3-MATH',
      subject: 'Mathematics',
      icon: '🔢',
      color: 'from-rose-400 to-pink-500',
      colorLight: 'bg-rose-50',
      totalLessons: 12,
      mastery: 25,
      status: 'in-progress',
      description: 'Explore numbers, basic operations, and mathematical symbols for Class 3 students.',
    },
    {
      id: 'class3-science',
      title: 'Class 3 Science NCTB',
      code: 'CLASS3-SCI',
      subject: 'Science',
      icon: '🔬',
      color: 'from-emerald-400 to-teal-500',
      colorLight: 'bg-emerald-50',
      totalLessons: 15,
      mastery: 0,
      status: 'not-started',
      description: 'Discover the wonders of science — plants, animals, weather, and the world around us.',
    },
    {
      id: 'class3-english',
      title: 'Class 3 English NCTB',
      code: 'CLASS3-ENG',
      subject: 'English',
      icon: '📖',
      color: 'from-amber-400 to-yellow-500',
      colorLight: 'bg-amber-50',
      totalLessons: 18,
      mastery: 0,
      status: 'not-started',
      description: 'Build your reading, writing, and communication skills in English.',
    },
  ],
  bn: [
    {
      id: 'class3-math',
      title: 'তৃতীয় শ্রেণি গণিত NCTB',
      code: 'CLASS3-MATH',
      subject: 'গণিত',
      icon: '🔢',
      color: 'from-rose-400 to-pink-500',
      colorLight: 'bg-rose-50',
      totalLessons: 12,
      mastery: 25,
      status: 'in-progress',
      description: 'তৃতীয় শ্রেণির শিক্ষার্থীদের জন্য সংখ্যা, মৌলিক অপারেশন এবং গাণিতিক চিহ্ন অন্বেষণ করুন।',
    },
    {
      id: 'class3-science',
      title: 'তৃতীয় শ্রেণি বিজ্ঞান NCTB',
      code: 'CLASS3-SCI',
      subject: 'বিজ্ঞান',
      icon: '🔬',
      color: 'from-emerald-400 to-teal-500',
      colorLight: 'bg-emerald-50',
      totalLessons: 15,
      mastery: 0,
      status: 'not-started',
      description: 'বিজ্ঞানের বিস্ময় আবিষ্কার করুন — গাছপালা, প্রাণী, আবহাওয়া এবং আমাদের চারপাশের পৃথিবী।',
    },
    {
      id: 'class3-english',
      title: 'তৃতীয় শ্রেণি ইংরেজি NCTB',
      code: 'CLASS3-ENG',
      subject: 'ইংরেজি',
      icon: '📖',
      color: 'from-amber-400 to-yellow-500',
      colorLight: 'bg-amber-50',
      totalLessons: 18,
      mastery: 0,
      status: 'not-started',
      description: 'ইংরেজিতে আপনার পড়া, লেখা এবং যোগাযোগ দক্ষতা তৈরি করুন।',
    },
  ],
};

export const lessonsData = {
  en: {
    'class3-math': {
      courseName: 'Class 3 Mathematics NCTB',
      courseIcon: '🔢',
      courseColor: 'from-rose-400 to-pink-500',
      progress: 25,
      lessons: [
        { id: 'counting', number: '1.1', title: 'Counting Numbers', description: 'Learn to count and identify numbers up to 1000', status: 'completed', mastery: 95, time: 15, questions: 10 },
        { id: 'addition', number: '1.2', title: 'Addition', description: 'Adding numbers with carrying', status: 'completed', mastery: 88, time: 20, questions: 12 },
        { id: 'math-symbols', number: '1.3', title: 'Mathematical Symbols', description: 'Understanding multiplication, division, and finding missing numbers', status: 'in-progress', mastery: 35, time: 25, questions: 15 },
        { id: 'subtraction', number: '1.4', title: 'Subtraction', description: 'Subtracting numbers with borrowing', status: 'available', mastery: 0, time: 20, questions: 12 },
        { id: 'multiplication', number: '1.5', title: 'Multiplication Tables', description: 'Learn multiplication tables up to 12', status: 'available', mastery: 0, time: 30, questions: 20 },
        { id: 'division', number: '1.6', title: 'Basic Division', description: 'Introduction to division and sharing equally', status: 'locked', mastery: 0, time: 25, questions: 15 },
        { id: 'fractions', number: '1.7', title: 'Fractions', description: 'Understanding halves, thirds, and quarters', status: 'locked', mastery: 0, time: 20, questions: 10 },
        { id: 'geometry', number: '1.8', title: 'Shapes and Geometry', description: 'Identifying and describing 2D and 3D shapes', status: 'locked', mastery: 0, time: 20, questions: 12 },
        { id: 'measurement', number: '1.9', title: 'Measurement', description: 'Length, weight, and capacity', status: 'locked', mastery: 0, time: 25, questions: 14 },
        { id: 'time', number: '1.10', title: 'Time', description: 'Reading clocks and understanding calendars', status: 'locked', mastery: 0, time: 15, questions: 10 },
        { id: 'money', number: '1.11', title: 'Money', description: 'Counting money and making change', status: 'locked', mastery: 0, time: 20, questions: 12 },
        { id: 'patterns', number: '1.12', title: 'Patterns', description: 'Recognizing and creating patterns', status: 'locked', mastery: 0, time: 15, questions: 8 },
      ],
    },
  },
  bn: {
    'class3-math': {
      courseName: 'তৃতীয় শ্রেণি গণিত NCTB',
      courseIcon: '🔢',
      courseColor: 'from-rose-400 to-pink-500',
      progress: 25,
      lessons: [
        { id: 'counting', number: '১.১', title: 'সংখ্যা গণনা', description: '১০০০ পর্যন্ত সংখ্যা গণনা ও শনাক্ত করা শিখুন', status: 'completed', mastery: 95, time: 15, questions: 10 },
        { id: 'addition', number: '১.২', title: 'যোগ', description: 'হাতে রেখে সংখ্যা যোগ করা', status: 'completed', mastery: 88, time: 20, questions: 12 },
        { id: 'math-symbols', number: '১.৩', title: 'গাণিতিক চিহ্ন', description: 'গুণ, ভাগ, এবং অনুপস্থিত সংখ্যা খোঁজা বোঝা', status: 'in-progress', mastery: 35, time: 25, questions: 15 },
        { id: 'subtraction', number: '১.৪', title: 'বিয়োগ', description: 'ধার করে সংখ্যা বিয়োগ করা', status: 'available', mastery: 0, time: 20, questions: 12 },
        { id: 'multiplication', number: '১.৫', title: 'নামতা', description: '১২ পর্যন্ত নামতা শিখুন', status: 'available', mastery: 0, time: 30, questions: 20 },
        { id: 'division', number: '১.৬', title: 'মৌলিক ভাগ', description: 'ভাগ এবং সমানভাবে ভাগ করার পরিচিতি', status: 'locked', mastery: 0, time: 25, questions: 15 },
        { id: 'fractions', number: '১.৭', title: 'ভগ্নাংশ', description: 'অর্ধেক, এক-তৃতীয়াংশ এবং এক-চতুর্থাংশ বোঝা', status: 'locked', mastery: 0, time: 20, questions: 10 },
        { id: 'geometry', number: '১.৮', title: 'আকৃতি ও জ্যামিতি', description: '2D এবং 3D আকৃতি শনাক্ত ও বর্ণনা করা', status: 'locked', mastery: 0, time: 20, questions: 12 },
        { id: 'measurement', number: '১.৯', title: 'পরিমাপ', description: 'দৈর্ঘ্য, ওজন এবং ধারণক্ষমতা', status: 'locked', mastery: 0, time: 25, questions: 14 },
        { id: 'time', number: '১.১০', title: 'সময়', description: 'ঘড়ি পড়া এবং ক্যালেন্ডার বোঝা', status: 'locked', mastery: 0, time: 15, questions: 10 },
        { id: 'money', number: '১.১১', title: 'টাকা', description: 'টাকা গণনা এবং ভাংতি দেওয়া', status: 'locked', mastery: 0, time: 20, questions: 12 },
        { id: 'patterns', number: '১.১২', title: 'প্যাটার্ন', description: 'প্যাটার্ন চিনুন এবং তৈরি করুন', status: 'locked', mastery: 0, time: 15, questions: 8 },
      ],
    },
  },
};

export const questionData = {
  en: {
    'math-symbols': {
      lessonTitle: 'Mathematical Symbols',
      questions: [
        {
          id: 'q1',
          question: '__ × 8 = 72',
          questionExplanation: 'Find the missing number that when multiplied by 8 gives 72.',
          correctAnswers: ['9', 'nine'],
          prerequisite: {
            skill: 'Division / Inverse of Multiplication',
            description: 'To find a missing factor, you need to understand that division is the inverse of multiplication.',
          },
          hints: [
            { id: 1, type: 'text', title: 'Understanding the Problem', content: 'We need to find a number that, when multiplied by 8, gives us 72. Think: "What number of groups of 8 makes 72?"' },
            { id: 2, type: 'text', title: 'What is Division?', content: 'Division is the opposite of multiplication! If __ × 8 = 72, we can flip it: 72 ÷ 8 = __.' },
            { id: 3, type: 'scaffolding', title: 'Converting to Division', content: 'To find the missing number, we need to divide. Can you write this as a division problem?', prompt: 'What is 72 divided by? (e.g., "72 ÷ 8")', correctAnswers: ['72÷8', '72/8', '72 ÷ 8', '72 / 8', '72 divided by 8'] },
            { id: 4, type: 'text', title: 'Solving Step by Step', content: 'Count by 8s: 8, 16, 24, 32, 40, 48, 56, 64, 72 ← that\'s 9 counts!\nOr: 8 × 9 = 72 ✓\nOr: 72 ÷ 8 = 9' },
          ],
          subLesson: {
            title: 'Mini-Lesson: Finding Missing Factors with Division',
            explanation: 'When you see __ × A = B, you can always find the answer by dividing: B ÷ A = __.\n\nExample: __ × 5 = 35  →  35 ÷ 5 = 7  ✓\nExample: __ × 4 = 28  →  28 ÷ 4 = 7  ✓',
            practiceQuestions: [
              { question: '__ × 6 = 42', correctAnswers: ['7', 'seven'], explanation: '42 ÷ 6 = 7' },
              { question: '__ × 7 = 56', correctAnswers: ['8', 'eight'], explanation: '56 ÷ 7 = 8' },
            ],
          },
        },
        {
          id: 'q2',
          question: '24 × 6 = __',
          questionExplanation: 'Multiply 24 by 6 to find the product.',
          correctAnswers: ['144'],
          prerequisite: {
            skill: 'Multi-digit Multiplication',
            description: 'Breaking larger multiplication into simpler parts using the distributive property.',
          },
          hints: [
            { id: 1, type: 'text', title: 'Breaking It Down', content: 'You can split 24 into parts you know:\n24 = 20 + 4\nSo: 24 × 6 = (20 × 6) + (4 × 6)' },
            { id: 2, type: 'scaffolding', title: 'Step 1: Multiply the tens', content: 'First, let\'s do the easy part. What is 20 × 6?', prompt: 'What is 20 × 6?', correctAnswers: ['120'] },
            { id: 3, type: 'scaffolding', title: 'Step 2: Multiply the ones', content: 'Now the second part. What is 4 × 6?', prompt: 'What is 4 × 6?', correctAnswers: ['24'] },
            { id: 4, type: 'text', title: 'Add Them Together', content: '20 × 6 = 120\n4 × 6 = 24\n120 + 24 = 144\n\nSo 24 × 6 = 144 ✓' },
          ],
          subLesson: {
            title: 'Mini-Lesson: The Distributive Property',
            explanation: 'For bigger multiplications, break the number apart:\n\nA × B = (tens of A × B) + (ones of A × B)\n\nExample: 13 × 5 = (10 × 5) + (3 × 5) = 50 + 15 = 65\nExample: 32 × 4 = (30 × 4) + (2 × 4) = 120 + 8 = 128',
            practiceQuestions: [
              { question: '15 × 4 = ?', correctAnswers: ['60'], explanation: '(10×4) + (5×4) = 40 + 20 = 60' },
              { question: '23 × 3 = ?', correctAnswers: ['69'], explanation: '(20×3) + (3×3) = 60 + 9 = 69' },
            ],
          },
        },
        {
          id: 'q3',
          question: '56 ÷ __ = 8',
          questionExplanation: 'Find the number that divides 56 to give 8.',
          correctAnswers: ['7', 'seven'],
          prerequisite: {
            skill: 'Division Facts',
            description: 'Using multiplication tables in reverse to solve division.',
          },
          hints: [
            { id: 1, type: 'text', title: 'Think Backwards', content: 'Division is the inverse of multiplication.\n56 ÷ __ = 8  is the same as  __ × 8 = 56' },
            { id: 2, type: 'text', title: 'Use Your Tables', content: 'Which number times 8 gives 56?\nTry: 6 × 8 = 48 ✗\n7 × 8 = 56 ✓' },
            { id: 3, type: 'scaffolding', title: 'Verify It', content: 'If the missing number is 7, what is 56 ÷ 7?', prompt: 'What is 56 ÷ 7?', correctAnswers: ['8', 'eight'] },
          ],
          subLesson: {
            title: 'Mini-Lesson: Multiplication-Division Connection',
            explanation: 'Every multiplication fact has a matching division fact:\n\nIf A × B = C, then C ÷ A = B and C ÷ B = A\n\nExample: 6 × 9 = 54  →  54 ÷ 6 = 9  and  54 ÷ 9 = 6',
            practiceQuestions: [
              { question: '48 ÷ __ = 6', correctAnswers: ['8', 'eight'], explanation: '8 × 6 = 48, so 48 ÷ 8 = 6' },
              { question: '63 ÷ __ = 9', correctAnswers: ['7', 'seven'], explanation: '7 × 9 = 63, so 63 ÷ 7 = 9' },
            ],
          },
        },
      ],
      initialMastery: 35,
    },
  },
  bn: {
    'math-symbols': {
      lessonTitle: 'গাণিতিক চিহ্ন',
      questions: [
        {
          id: 'q1',
          question: '__ × ৮ = ৭২',
          questionExplanation: 'সেই অনুপস্থিত সংখ্যাটি খুঁজুন যা ৮ দিয়ে গুণ করলে ৭২ হয়।',
          correctAnswers: ['9', '৯', 'নয়'],
          prerequisite: {
            skill: 'ভাগ / গুণের বিপরীত',
            description: 'অনুপস্থিত গুণনীয়ক খুঁজতে, আপনাকে বুঝতে হবে যে ভাগ হলো গুণের বিপরীত।',
          },
          hints: [
            { id: 1, type: 'text', title: 'সমস্যাটি বুঝুন', content: 'আমাদের এমন একটি সংখ্যা খুঁজতে হবে যা ৮ দিয়ে গুণ করলে ৭২ হয়। ভাবুন: "৮-এর কতগুলি দল মিলে ৭২ হয়?"' },
            { id: 2, type: 'text', title: 'ভাগ কী?', content: 'ভাগ হলো গুণের উল্টো! যদি __ × ৮ = ৭২, তাহলে ৭২ ÷ ৮ = __।' },
            { id: 3, type: 'scaffolding', title: 'ভাগে রূপান্তর', content: 'অনুপস্থিত সংখ্যা খুঁজতে ভাগ করুন।', prompt: '৭২ কে কত দিয়ে ভাগ? (যেমন, "৭২ ÷ ৮")', correctAnswers: ['72÷8', '72/8', '72 ÷ 8', '৭২÷৮', '৭২ ÷ ৮'] },
            { id: 4, type: 'text', title: 'ধাপে ধাপে সমাধান', content: '৮ গুণে গণনা: ৮, ১৬, ২৪, ৩২, ৪০, ৪৮, ৫৬, ৬৪, ৭২ ← সেটি ৯ বার!\n৮ × ৯ = ৭২ ✓\n৭২ ÷ ৮ = ৯' },
          ],
          subLesson: {
            title: 'মিনি-পাঠ: ভাগ দিয়ে অনুপস্থিত গুণনীয়ক খোঁজা',
            explanation: '__ × A = B দেখলে, উত্তর পেতে ভাগ করুন: B ÷ A = __\n\nউদাহরণ: __ × ৫ = ৩৫ → ৩৫ ÷ ৫ = ৭ ✓\nউদাহরণ: __ × ৪ = ২৮ → ২৮ ÷ ৪ = ৭ ✓',
            practiceQuestions: [
              { question: '__ × ৬ = ৪২', correctAnswers: ['7', '৭', 'সাত'], explanation: '৪২ ÷ ৬ = ৭' },
              { question: '__ × ৭ = ৫৬', correctAnswers: ['8', '৮', 'আট'], explanation: '৫৬ ÷ ৭ = ৮' },
            ],
          },
        },
        {
          id: 'q2',
          question: '২৪ × ৬ = __',
          questionExplanation: 'গুণফল বের করতে ২৪ কে ৬ দিয়ে গুণ করুন।',
          correctAnswers: ['144', '১৪৪'],
          prerequisite: {
            skill: 'বহু-অঙ্কের গুণ',
            description: 'বিতরণ ধর্ম ব্যবহার করে বড় গুণকে সহজ অংশে ভাঙা।',
          },
          hints: [
            { id: 1, type: 'text', title: 'ভেঙে দিন', content: '২৪ কে ভাগ করুন:\n২৪ = ২০ + ৪\nতাই: ২৪ × ৬ = (২০ × ৬) + (৪ × ৬)' },
            { id: 2, type: 'scaffolding', title: 'ধাপ ১: দশক গুণ', content: 'প্রথমে সহজ অংশ। ২০ × ৬ কত?', prompt: '২০ × ৬ কত?', correctAnswers: ['120', '১২০'] },
            { id: 3, type: 'scaffolding', title: 'ধাপ ২: একক গুণ', content: 'এবার দ্বিতীয় অংশ। ৪ × ৬ কত?', prompt: '৪ × ৬ কত?', correctAnswers: ['24', '২৪'] },
            { id: 4, type: 'text', title: 'যোগ করুন', content: '২০ × ৬ = ১২০\n৪ × ৬ = ২৪\n১২০ + ২৪ = ১৪৪\n\nতাই ২৪ × ৬ = ১৪৪ ✓' },
          ],
          subLesson: {
            title: 'মিনি-পাঠ: বিতরণ ধর্ম',
            explanation: 'বড় গুণের জন্য, সংখ্যাটি ভেঙে নিন:\n\nA × B = (A-এর দশক × B) + (A-এর একক × B)\n\nউদাহরণ: ১৩ × ৫ = (১০ × ৫) + (৩ × ৫) = ৫০ + ১৫ = ৬৫\nউদাহরণ: ৩২ × ৪ = (৩০ × ৪) + (২ × ৪) = ১২০ + ৮ = ১২৮',
            practiceQuestions: [
              { question: '১৫ × ৪ = ?', correctAnswers: ['60', '৬০'], explanation: '(১০×৪) + (৫×৪) = ৪০ + ২০ = ৬০' },
              { question: '২৩ × ৩ = ?', correctAnswers: ['69', '৬৯'], explanation: '(২০×৩) + (৩×৩) = ৬০ + ৯ = ৬৯' },
            ],
          },
        },
        {
          id: 'q3',
          question: '৫৬ ÷ __ = ৮',
          questionExplanation: '৫৬ কে ভাগ করে ৮ পেতে কোন সংখ্যা দিয়ে ভাগ করতে হবে খুঁজুন।',
          correctAnswers: ['7', '৭', 'সাত'],
          prerequisite: {
            skill: 'ভাগের তথ্য',
            description: 'ভাগ সমাধানে গুণের নামতা উল্টো ব্যবহার।',
          },
          hints: [
            { id: 1, type: 'text', title: 'উল্টো ভাবুন', content: 'ভাগ হলো গুণের বিপরীত।\n৫৬ ÷ __ = ৮ মানে __ × ৮ = ৫৬' },
            { id: 2, type: 'text', title: 'নামতা ব্যবহার করুন', content: 'কোন সংখ্যা × ৮ = ৫৬?\n৬ × ৮ = ৪৮ ✗\n৭ × ৮ = ৫৬ ✓' },
            { id: 3, type: 'scaffolding', title: 'যাচাই করুন', content: 'উত্তর ৭ হলে, ৫৬ ÷ ৭ কত?', prompt: '৫৬ ÷ ৭ কত?', correctAnswers: ['8', '৮', 'আট'] },
          ],
          subLesson: {
            title: 'মিনি-পাঠ: গুণ-ভাগ সম্পর্ক',
            explanation: 'প্রতিটি গুণের তথ্যের একটি মিলিত ভাগের তথ্য আছে:\n\nA × B = C হলে, C ÷ A = B এবং C ÷ B = A\n\nউদাহরণ: ৬ × ৯ = ৫৪ → ৫৪ ÷ ৬ = ৯ এবং ৫৪ ÷ ৯ = ৬',
            practiceQuestions: [
              { question: '৪৮ ÷ __ = ৬', correctAnswers: ['8', '৮', 'আট'], explanation: '৮ × ৬ = ৪৮, তাই ৪৮ ÷ ৮ = ৬' },
              { question: '৬৩ ÷ __ = ৯', correctAnswers: ['7', '৭', 'সাত'], explanation: '৭ × ৯ = ৬৩, তাই ৬৩ ÷ ৭ = ৯' },
            ],
          },
        },
      ],
      initialMastery: 35,
    },
  },
};
