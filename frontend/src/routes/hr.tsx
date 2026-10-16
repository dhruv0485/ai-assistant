import {createFileRoute,Outlet} from '@tanstack/react-router';
import {pageHead} from '@/lib/tribe-data';
export const Route=createFileRoute('/hr')({validateSearch:(s:Record<string,unknown>):{view?:string}=>(typeof s['view']==='string'?{view:s['view']}:{}),head:()=>pageHead('HR Workspace','Placement drive job and candidate management for hiring teams.'),component:Outlet});
