import { createFileRoute, Link } from '@tanstack/react-router';
import { HowSteps } from '@/components/home-content';
import { pageHead } from '@/lib/tribe-data';
import { Button } from '@/components/ui/button';
import { ArrowRight } from 'lucide-react';
export const Route=createFileRoute('/how-it-works')({head:()=>pageHead('How It Works','Explore the eight-stage screening architecture: parsing, extraction, semantic alignment, evidence, confidence, human review and fairness auditing.'),component:Page});
function Page(){return <main><HowSteps/><div className="container pb-16 text-center"><Button asChild><Link to="/check-score">Upload Resume &amp; Check Score<ArrowRight/></Link></Button></div></main>}
