import { motion } from 'framer-motion';
import { Clock, Target, Zap, Shield, Sparkles, CheckCircle2, ArrowRight, BarChart3, FileText, Wand2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <Hero />
      <PulseSection />
      <FeaturesCardsSection />
      <AICompetencySection />
      <QualitySection />
      <CTASection />
      <Footer />
    </div>
  );
}

function Hero() {
  return (
    <section className="pt-32 pb-20 px-6">
      <div className="max-w-5xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <h1 className="text-5xl md:text-7xl font-bold text-slate-900 tracking-tight leading-[1.1] mb-6">
            The End of Doom-Scrolling<br />for Jobs.
          </h1>
          <p className="text-lg md:text-xl text-slate-600 max-w-3xl mx-auto leading-relaxed font-light">
            A no-nonsense platform where jobs update once a day. Spend 5 minutes finding the right match, and 15 minutes making a world-class application.
          </p>
        </motion.div>
      </div>
    </section>
  );
}

function PulseSection() {
  const [timeUntilRefresh, setTimeUntilRefresh] = useState('');

  useEffect(() => {
    const calculateTimeUntilRefresh = () => {
      const now = new Date();
      const tomorrow = new Date();
      tomorrow.setHours(24, 0, 0, 0);

      const diff = tomorrow.getTime() - now.getTime();
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    };

    setTimeUntilRefresh(calculateTimeUntilRefresh());
    const interval = setInterval(() => {
      setTimeUntilRefresh(calculateTimeUntilRefresh());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <section className="py-20 px-6 bg-gradient-to-b from-white to-cyan-50">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="border border-cyan-200 rounded-2xl p-8 md:p-12 bg-white shadow-sm"
        >
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-4">
                <Clock className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />
                <h2 className="text-2xl md:text-3xl font-semibold text-slate-900">24-Hour Pulse</h2>
              </div>
              <p className="text-slate-600 text-base leading-relaxed">
                Every job on Inclusist is fresh. Maximum 24-hour lag from creation. No stale posts, no expired opportunities.
              </p>
            </div>
            <div className="flex-shrink-0">
              <div className="text-center">
                <div className="text-sm text-slate-600 mb-2 uppercase tracking-wide">Next Daily Sync</div>
                <div className="text-4xl md:text-5xl font-bold text-cyan-600 tabular-nums tracking-tight">
                  {timeUntilRefresh}
                </div>
                <div className="mt-3 inline-flex items-center space-x-2 px-4 py-2 bg-emerald-50 rounded-full">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-emerald-700 font-medium">Live</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function FeaturesCardsSection() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-3 gap-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="border border-cyan-200 rounded-2xl p-8 bg-white shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-center space-x-3 mb-6">
              <BarChart3 className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />
              <h3 className="text-2xl font-semibold text-slate-900">Smart Dashboard</h3>
            </div>
            <p className="text-slate-600 mb-6 leading-relaxed">
              Track all your shortlisted jobs in one place. Monitor applications, deadlines, and match scores with crystal clarity.
            </p>
            <div className="inline-flex items-center space-x-2 px-3 py-1.5 bg-cyan-50 rounded-full">
              <CheckCircle2 className="w-4 h-4 text-cyan-600" />
              <span className="text-sm text-cyan-700 font-medium">Organized & Simple</span>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="border border-cyan-200 rounded-2xl p-8 bg-white shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-center space-x-3 mb-6">
              <FileText className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />
              <h3 className="text-2xl font-semibold text-slate-900">Tailored Resumes</h3>
            </div>
            <p className="text-slate-600 mb-6 leading-relaxed">
              Generate custom resumes optimized for each job in seconds. Our AI highlights your most relevant qualifications.
            </p>
            <div className="inline-flex items-center space-x-2 px-3 py-1.5 bg-emerald-50 rounded-full">
              <Zap className="w-4 h-4 text-emerald-600" />
              <span className="text-sm text-emerald-700 font-medium">Instant Creation</span>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="border border-cyan-200 rounded-2xl p-8 bg-white shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-center space-x-3 mb-6">
              <Wand2 className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />
              <h3 className="text-2xl font-semibold text-slate-900">Cover Letters</h3>
            </div>
            <p className="text-slate-600 mb-6 leading-relaxed">
              Craft compelling cover letters on the fly. AI-powered suggestions ensure every letter is personalized and persuasive.
            </p>
            <div className="inline-flex items-center space-x-2 px-3 py-1.5 bg-amber-50 rounded-full">
              <Sparkles className="w-4 h-4 text-amber-600" />
              <span className="text-sm text-amber-700 font-medium">AI Enhanced</span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function AICompetencySection() {
  return (
    <section id="how-it-works" className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">Matches, not Keywords.</h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            We match your competency—knowledge and skills—against job requirements using deep AI analysis.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="border border-cyan-200 rounded-xl p-8 bg-white hover:shadow-lg transition-shadow"
          >
            <div className="w-12 h-12 bg-cyan-600 rounded-lg flex items-center justify-center mb-6">
              <Sparkles className="w-6 h-6 text-white" strokeWidth={1.5} />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-4">Deep Analysis</h3>
            <p className="text-slate-600 leading-relaxed">
              Our AI doesn't just scan for keywords. It understands the depth of your experience and the true requirements of each role.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="border border-cyan-200 rounded-xl p-8 bg-white hover:shadow-lg transition-shadow"
          >
            <div className="w-12 h-12 bg-cyan-600 rounded-lg flex items-center justify-center mb-6">
              <Target className="w-6 h-6 text-white" strokeWidth={1.5} />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-4">Competency Score</h3>
            <p className="text-slate-600 leading-relaxed">
              Get a precise match percentage based on your skills, knowledge, and the job's actual needs—not just buzzwords.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="border border-cyan-200 rounded-xl p-8 bg-white hover:shadow-lg transition-shadow"
          >
            <div className="w-12 h-12 bg-cyan-600 rounded-lg flex items-center justify-center mb-6">
              <Zap className="w-6 h-6 text-white" strokeWidth={1.5} />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-4">Smart Guidance</h3>
            <p className="text-slate-600 leading-relaxed">
              Receive actionable insights on why a job fits you, and what to emphasize in your application.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function QualitySection() {
  const qualities = [
    {
      icon: Shield,
      title: "Zero Noise",
      description: "No ads, no sponsored junk, no repeat posts. Just real opportunities from verified employers."
    },
    {
      icon: Target,
      title: "Competency Match",
      description: "AI-scored guidance on why a job fits your specific skill set, with transparency on strengths and gaps."
    },
    {
      icon: CheckCircle2,
      title: "Deep Focus",
      description: "Tools designed to help you build a strong, tailored application once a match is found."
    }
  ];

  return (
    <section id="quality" className="py-20 px-6 bg-gradient-to-b from-cyan-50 to-white">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">Quality Over Quantity</h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            We believe in precision, not volume. Find the right job, not just any job.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6">
          {qualities.map((quality, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="border border-cyan-200 rounded-xl p-8 bg-white hover:border-cyan-400 transition-colors"
            >
              <quality.icon className="w-8 h-8 text-cyan-600 mb-4" strokeWidth={1.5} />
              <h3 className="text-xl font-semibold text-slate-900 mb-3">{quality.title}</h3>
              <p className="text-slate-600 leading-relaxed">{quality.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section id="cta" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="bg-gradient-to-br from-cyan-600 to-cyan-700 rounded-2xl p-12 md:p-16 text-center relative overflow-hidden"
        >
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full mix-blend-screen blur-3xl"></div>
          </div>
          <div className="relative z-10">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">
              Ready to stop scrolling?
            </h2>
            <p className="text-lg text-cyan-100 mb-12 max-w-2xl mx-auto">
              Join thousands finding meaningful roles with precision and clarity.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Link
                  to="/login"
                  className="px-8 py-4 bg-white text-cyan-600 font-semibold rounded-lg hover:bg-cyan-50 transition-colors flex items-center justify-center gap-2"
                >
                  Join Now
                  <ArrowRight className="w-5 h-5" />
                </Link>
              </motion.div>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Link
                  to="/login"
                  className="px-8 py-4 bg-cyan-500 text-white font-semibold rounded-lg hover:bg-cyan-400 transition-colors flex items-center justify-center gap-2"
                >
                  Login
                  <ArrowRight className="w-5 h-5" />
                </Link>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
