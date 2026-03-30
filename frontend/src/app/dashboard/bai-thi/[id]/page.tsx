import ExamPage from "./ExamPage";

// Generate static pages for all exam IDs
// TODO: Fetch actual exam IDs from API or database
export async function generateStaticParams() {
    // For now, return empty array to skip static generation
    // This page will be client-side only
    return [];
}

// Force this page to be static (no server-side rendering)
export const dynamic = 'force-static';
export const dynamicParams = true; // Allow dynamic params at runtime

export default function Page() {
    return <ExamPage />;
}
