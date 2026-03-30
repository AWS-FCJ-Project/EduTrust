import ExamPage from "./ExamPage";

// Force dynamic rendering for user-specific exam data
// This page requires authentication and real-time data
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default function Page() {
    return <ExamPage />;
}
