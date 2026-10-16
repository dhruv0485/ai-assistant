import { photos } from '@/lib/photos';
import { createFileRoute } from '@tanstack/react-router';
import { HomeContent } from '@/components/home-content';
import { pageHead } from '@/lib/tribe-data';
export const Route=createFileRoute('/')({head:()=>pageHead('Resume Fit Score','See how well your resume fits the job — before you apply. Upload your resume and compare it with a job description, with no sign-up needed.', photos[0]),component:HomeContent});
