import { Navigate, Route, Routes } from 'react-router-dom';
import AgentExecutePage from '@/pages/AgentExecutePage';
import AppLayout from '@/layouts/AppLayout';
import BenchmarkLabPage from '@/pages/BenchmarkLabPage';
import DocumentDetailPage from '@/pages/DocumentDetailPage';
import FactsReviewPage from '@/pages/FactsReviewPage';
import UploadPage from '@/pages/uploadPage';

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/upload" replace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/documents" element={<DocumentDetailPage />} />
        <Route path="/facts" element={<FactsReviewPage />} />
        <Route path="/agent" element={<AgentExecutePage />} />
        <Route path="/benchmarks" element={<BenchmarkLabPage />} />
      </Route>
    </Routes>
  );
}