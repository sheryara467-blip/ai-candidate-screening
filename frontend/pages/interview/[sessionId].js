// ============================================================
// EXACT FILE LOCATION: frontend/pages/interview/[sessionId].js
// ============================================================
// PURPOSE: Candidate interview page.
// Shows one question at a time, lets candidate answer via
// text or voice, navigates between questions, submits all.
//
// URL: /interview/{sessionId}
// ============================================================

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import CandidateLayout from "../../components/candidate/CandidateLayout";
import {
  getInterviewSession,
  startInterview,
  submitTextAnswer,
  transcribeVoice,
  getQuestionAudio,
  evaluateInterview,
} from "../../services/api";
import toast from "react-hot-toast";
import {
  Mic, MicOff, Play, Send, ChevronRight,
  ChevronLeft, CheckCircle, Volume2, Loader,
} from "lucide-react";

// Category badge colors
const CAT_COLORS = {
  TECHNICAL:       "bg-blue-100 text-blue-700",
  BEHAVIORAL:      "bg-purple-100 text-purple-700",
  PROBLEM_SOLVING: "bg-orange-100 text-orange-700",
};

export default function InterviewPage() {
  const router              = useRouter();
  const { sessionId }       = router.query;

  const [session,         setSession]         = useState(null);
  const [currentIdx,      setCurrentIdx]      = useState(0);
  const [answers,         setAnswers]         = useState({});   // {questionId: text}
  const [loading,         setLoading]         = useState(true);
  const [submitting,       setSubmitting]      = useState(false);
  const [evaluating,       setEvaluating]      = useState(false);
  const [isRecording,     setIsRecording]     = useState(false);
  const [audioLoading,    setAudioLoading]    = useState(false);
  const [completed,        setCompleted]       = useState(false);
  const [evalResult,       setEvalResult]      = useState(null);

  const mediaRecorderRef  = useRef(null);
  const audioChunksRef    = useRef([]);
  const audioPlayerRef    = useRef(null);

  // Load session on mount
  useEffect(() => {
    if (!sessionId) return;
    fetchSession();
  }, [sessionId]);

  const fetchSession = async () => {
    try {
      setLoading(true);
      const data = await getInterviewSession(sessionId);
      setSession(data);

      // Mark session as started
      if (data.status === "PENDING") {
        await startInterview(sessionId);
      }

      // Pre-fill any already-saved answers
      const saved = {};
      data.questions.forEach((q) => {
        if (q.answer?.answer_text) {
          saved[q.id] = q.answer.answer_text;
        }
      });
      setAnswers(saved);
    } catch (err) {
      toast.error("Failed to load interview session");
    } finally {
      setLoading(false);
    }
  };

  const currentQuestion = session?.questions?.[currentIdx];
  const totalQuestions  = session?.questions?.length || 0;
  const currentAnswer   = answers[currentQuestion?.id] || "";

  // ============================================================
  // Play TTS audio for current question
  // ============================================================
  const handlePlayAudio = async () => {
    if (!currentQuestion) return;
    setAudioLoading(true);
    try {
      const result = await getQuestionAudio(currentQuestion.id);
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = `${process.env.NEXT_PUBLIC_API_URL}${result.audio_url}`;
        audioPlayerRef.current.play();
      }
    } catch (err) {
      toast.error("Audio generation failed");
    } finally {
      setAudioLoading(false);
    }
  };

  // ============================================================
  // Start / stop voice recording
  // ============================================================
  const handleToggleRecording = async () => {
    if (isRecording) {
      // Stop recording
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
    } else {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        audioChunksRef.current = [];

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        recorder.onstop = async () => {
          // Upload and transcribe the recording
          const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          const file = new File([blob], "answer.webm", { type: "audio/webm" });
          await handleTranscribe(file);
          stream.getTracks().forEach((t) => t.stop());
        };

        recorder.start();
        mediaRecorderRef.current = recorder;
        setIsRecording(true);
        toast("Recording... click again to stop", { icon: "🎙️" });
      } catch (err) {
        toast.error("Microphone access denied");
      }
    }
  };

  // ============================================================
  // Upload voice recording and get transcript
  // ============================================================
  const handleTranscribe = async (file) => {
    if (!currentQuestion) return;
    toast.loading("Transcribing...", { id: "transcribe" });
    try {
      const result = await transcribeVoice(session.id, currentQuestion.id, file);
      setAnswers((prev) => ({ ...prev, [currentQuestion.id]: result.transcript }));
      toast.success("Voice transcribed", { id: "transcribe" });
    } catch (err) {
      toast.error("Transcription failed — please type your answer", { id: "transcribe" });
    }
  };

  // ============================================================
  // Save current answer and move to next question
  // ============================================================
  const handleNext = async () => {
    if (!currentAnswer.trim()) {
      toast.error("Please provide an answer before continuing");
      return;
    }
    setSubmitting(true);
    try {
      await submitTextAnswer({
        session_id:  session.id,
        question_id: currentQuestion.id,
        answer_text: currentAnswer,
        answer_type: "TEXT",
      });

      if (currentIdx < totalQuestions - 1) {
        setCurrentIdx((i) => i + 1);
      }
    } catch (err) {
      toast.error("Failed to save answer");
    } finally {
      setSubmitting(false);
    }
  };

  // ============================================================
  // Submit all answers and trigger AI evaluation
  // ============================================================
  const handleSubmitAll = async () => {
    if (!currentAnswer.trim()) {
      toast.error("Please answer the current question first");
      return;
    }

    // Save last answer first
    setSubmitting(true);
    try {
      await submitTextAnswer({
        session_id:  session.id,
        question_id: currentQuestion.id,
        answer_text: currentAnswer,
        answer_type: "TEXT",
      });
    } catch {
      // Ignore if already saved
    }
    setSubmitting(false);

    // Run AI evaluation
    setEvaluating(true);
    toast.loading("AI is evaluating your answers...", { id: "eval" });
    try {
      const result = await evaluateInterview(session.id);
      setEvalResult(result);
      setCompleted(true);
      toast.success("Interview complete!", { id: "eval" });
    } catch (err) {
      toast.error("Evaluation failed: " + (err.userMessage || "Try again"), { id: "eval" });
    } finally {
      setEvaluating(false);
    }
  };

  // ============================================================
  // COMPLETION SCREEN
  // ============================================================
  if (completed && evalResult) {
    return (
      <CandidateLayout title="Interview Complete">
        <div className="max-w-2xl mx-auto py-10 text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
            <CheckCircle size={36} className="text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Interview Submitted!</h1>
          <p className="text-gray-500 mb-8">
            Your interview has been evaluated by our AI system.
          </p>

          {/* Score */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6 text-left">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Interview Score</h2>
              <span className={`text-2xl font-bold ${evalResult.interview_score >= 60 ? "text-green-600" : "text-red-500"}`}>
                {evalResult.interview_score?.toFixed(0)}%
              </span>
            </div>
            <p className="text-sm text-gray-600">{evalResult.overall_feedback}</p>
          </div>

          <Link href="/careers" className="btn-primary">
            Browse More Jobs
          </Link>
        </div>
      </CandidateLayout>
    );
  }

  // ============================================================
  // LOADING STATE
  // ============================================================
  if (loading) {
    return (
      <CandidateLayout title="Interview">
        <div className="max-w-2xl mx-auto animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/2" />
          <div className="h-32 bg-gray-200 rounded" />
          <div className="h-24 bg-gray-200 rounded" />
        </div>
      </CandidateLayout>
    );
  }

  if (!session || !currentQuestion) {
    return (
      <CandidateLayout title="Interview">
        <div className="text-center py-20">
          <p className="text-gray-500">No interview session found.</p>
          <Link href="/careers" className="btn-primary mt-4 inline-flex">Browse Jobs</Link>
        </div>
      </CandidateLayout>
    );
  }

  // ============================================================
  // MAIN INTERVIEW UI
  // ============================================================
  return (
    <CandidateLayout title="AI Interview">
      <audio ref={audioPlayerRef} className="hidden" />

      <div className="max-w-2xl mx-auto">
        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex justify-between text-xs text-gray-400 mb-1.5">
            <span>Question {currentIdx + 1} of {totalQuestions}</span>
            <span>{Math.round(((currentIdx) / totalQuestions) * 100)}% complete</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${((currentIdx) / totalQuestions) * 100}%` }}
            />
          </div>
        </div>

        {/* Question card */}
        <div className="bg-white rounded-xl border border-gray-200 p-7 mb-5">
          {/* Category badge + audio button */}
          <div className="flex items-center justify-between mb-4">
            <span className={`text-xs font-semibold px-3 py-1 rounded-full ${CAT_COLORS[currentQuestion.category] || "bg-gray-100 text-gray-600"}`}>
              {currentQuestion.category?.replace("_", " ")}
            </span>
            <button
              onClick={handlePlayAudio}
              disabled={audioLoading}
              title="Listen to question"
              className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              {audioLoading ? <Loader size={14} className="animate-spin" /> : <Volume2 size={14} />}
              Listen
            </button>
          </div>

          {/* Question text */}
          <p className="text-lg font-semibold text-gray-900 leading-relaxed">
            {currentQuestion.question_text}
          </p>
        </div>

        {/* Answer area */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-5">
          <p className="text-sm font-medium text-gray-700 mb-3">Your Answer</p>

          <textarea
            value={currentAnswer}
            onChange={(e) =>
              setAnswers((prev) => ({ ...prev, [currentQuestion.id]: e.target.value }))
            }
            rows={5}
            placeholder="Type your answer here..."
            className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none transition"
          />

          {/* Voice recording button */}
          <div className="flex items-center gap-3 mt-3">
            <button
              onClick={handleToggleRecording}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                isRecording
                  ? "bg-red-100 text-red-700 border border-red-300 animate-pulse"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {isRecording ? <><MicOff size={15} /> Stop Recording</> : <><Mic size={15} /> Record Voice</>}
            </button>
            {isRecording && (
              <span className="text-xs text-red-500 font-medium">● Recording...</span>
            )}
          </div>
        </div>

        {/* Navigation buttons */}
        <div className="flex gap-3">
          {/* Previous */}
          {currentIdx > 0 && (
            <button
              onClick={() => setCurrentIdx((i) => i - 1)}
              className="flex items-center gap-2 px-4 py-2.5 border border-gray-300 text-gray-600 text-sm font-medium rounded-xl hover:bg-gray-50 transition-colors"
            >
              <ChevronLeft size={16} /> Previous
            </button>
          )}

          {/* Next or Submit */}
          {currentIdx < totalQuestions - 1 ? (
            <button
              onClick={handleNext}
              disabled={submitting || !currentAnswer.trim()}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {submitting ? <Loader size={15} className="animate-spin" /> : null}
              Next Question <ChevronRight size={16} />
            </button>
          ) : (
            <button
              onClick={handleSubmitAll}
              disabled={evaluating || !currentAnswer.trim()}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-green-600 text-white text-sm font-semibold rounded-xl hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {evaluating ? <Loader size={15} className="animate-spin" /> : <Send size={15} />}
              {evaluating ? "Evaluating..." : "Submit Interview"}
            </button>
          )}
        </div>
      </div>
    </CandidateLayout>
  );
}