import {defineConfig} from 'vite';
// Development inspection only; deployment still uses the existing static copy build.
export default defineConfig({root:'public',publicDir:false,server:{host:'0.0.0.0',allowedHosts:['terminal.local'],port:4173,strictPort:true}});
