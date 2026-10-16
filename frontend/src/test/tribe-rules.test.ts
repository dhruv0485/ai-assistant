import {describe,it,expect} from 'vitest';
import {isShortlisted,validateDocument,matchSkills,MAX_FILE_BYTES} from '@/lib/scoring';
describe('Placement drive rules',()=>{
 it('shortlists a score of 60 at the default threshold',()=>{expect(isShortlisted(60)).toBe(true);expect(isShortlisted(59)).toBe(false)});
 it('uses a changed threshold including the boundary',()=>{expect(isShortlisted(72,73)).toBe(false);expect(isShortlisted(73,73)).toBe(true)});
 it('permits PDF and DOCX and rejects other document formats',()=>{expect(validateDocument({name:'Resume.pdf',size:10})).toBe('');expect(validateDocument({name:'Resume.docx',size:10})).toBe('');expect(validateDocument({name:'Resume.txt',size:10})).toBe('Please upload a PDF or DOCX file.')});
 it('limits uploaded documents to 5 MB',()=>{expect(MAX_FILE_BYTES).toBe(5242880);expect(validateDocument({name:'Resume.pdf',size:5242880})).toBe('');expect(validateDocument({name:'Resume.pdf',size:5242881})).toBe('File must be 5 MB or smaller.')});
 it('matches React.js with React and calculates a concrete keyword score',()=>{expect(matchSkills('React.js and Git',['React','TypeScript','Git'])).toEqual({matched:['React','Git'],missing:['TypeScript'],score:67})});
});
