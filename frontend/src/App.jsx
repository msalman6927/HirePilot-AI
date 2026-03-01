import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import CVUpload from './pages/CVUpload';
import Chatbot from './pages/Chatbot';
import JobMatching from './pages/JobMatching';
import ApplicationPrep from './pages/ApplicationPrep';
import InterviewPrep from './pages/InterviewPrep';
import Dashboard from './pages/Dashboard';

export default function App() {
  return (
    <div className="flex min-h-screen bg-[#0a0e1a]">
      <Sidebar />
      <main className="ml-[72px] flex-1 min-h-screen">
        <Routes>
          <Route path="/" element={<CVUpload />} />
          <Route path="/chat" element={<Chatbot />} />
          <Route path="/jobs" element={<JobMatching />} />
          <Route path="/apply" element={<ApplicationPrep />} />
          <Route path="/interview-prep" element={<InterviewPrep />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  );
}
