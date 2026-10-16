import {createFileRoute} from '@tanstack/react-router';
import {pageHead} from '@/lib/tribe-data';
export const Route=createFileRoute('/terms')({head:()=>pageHead('Terms','Terms for using the Hunt Your Tribe placement drive tool.'),component:Page});
function Page(){return <main className="container page-main form-narrow"><h1 className="page-title">Terms</h1><p className="page-subtitle">Terms for using the Hunt Your Tribe placement drive tool.</p><div className="jd-content"><p>Fit scores are guidance, not a hiring decision or a guarantee of placement. Submit only accurate information and documents you have permission to share. Hiring decisions remain with the recruiting team. The placement drive organizer must supply the final terms before launch.</p></div></main>}
