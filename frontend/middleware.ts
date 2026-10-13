import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Protect workspace routes
  if (pathname.startsWith('/dashboard') || 
      pathname.startsWith('/threats') || 
      pathname.startsWith('/candidates') || 
      pathname.startsWith('/brands') || 
      pathname.startsWith('/cases') || 
      pathname.startsWith('/analytics')) {
    
    // In a real app, check auth token here
    // For demo, we'll allow access but could redirect to /login
    return NextResponse.next();
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/threats/:path*', '/candidates/:path*', '/brands/:path*', '/cases/:path*', '/analytics/:path*']
};