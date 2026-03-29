"use client";
import { Sidebar } from '@/components/ui/sidebar';
import { Bell } from 'lucide-react';
import Image from 'next/image';
import study from '../../../public/study.png';
import { LogOut, ChevronDown } from 'lucide-react';
import Cookies from 'js-cookie';
import { ProfilePopover } from '@/components/dashboard/ProfilePopover';

import { useEffect, useState } from 'react';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [isProfileOpen, setIsProfileOpen] = useState(false);

    useEffect(() => {
        const fetchUserInfo = async () => {
            try {
                const token = Cookies.get('auth_token');
                if (!token) {
                    window.location.href = '/login';
                    return;
                }

                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/user-info`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    setUser(data);
                } else {
                    Cookies.remove('auth_token');
                    window.location.href = '/login';
                }
            } catch (error) {
                console.error("Error fetching user info:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchUserInfo();
    }, []);

    if (loading) return <div className="flex h-screen w-full items-center justify-center bg-[#F0F2F5]">Loading...</div>;
    if (!user) return null;

    const role = user.role;
    const handleLogout = async () => {
        try {
            const token = Cookies.get('auth_token');

            await fetch(`${process.env.NEXT_PUBLIC_API_URL}/logout`, {
                method: 'POST',
                headers: {
                    'accept': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
        } catch (error) {
            console.error("Lỗi gọi API logout:", error);
        } finally {
            Cookies.remove('auth_token', { path: '/' });
            window.location.href = '/';
        }
    };
    return (
        <div className="flex h-screen w-full bg-[#F0F2F5] overflow-hidden">
            <Sidebar role={role} />

            <main className="flex-1 flex flex-col min-w-0">
                <header className="h-16 bg-white flex items-center justify-between px-8 shadow-sm z-10 shrink-0">
                    <h2 className="text-gray-700 font-bold text-lg">
                        Chào {user.name || 'Người dùng'}! 👋
                    </h2>
                    <div className="flex items-center gap-6">
                        <button className="relative p-1"><Bell size={20} /></button>
                        
                        {/* User Profile Section */}
                        <div className="relative">
                            <button 
                                onClick={() => setIsProfileOpen(!isProfileOpen)}
                                className="flex items-center gap-3 border border-gray-200 bg-white ml-4 px-4 py-2 rounded-2xl shadow-sm hover:border-[#5B0019]/30 transition-all active:scale-95 group"
                            >
                                <div className="text-right hidden sm:block">
                                    <p className="text-sm font-bold text-gray-700">{user.name || 'Người dùng'}</p>
                                    <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">{user.role}</p>
                                </div>
                                <div className="w-10 h-10 rounded-full relative overflow-hidden border-2 border-white shadow-sm group-hover:border-[#5B0019]/20 transition-all">
                                    <Image src={study} alt="Avatar" fill className="object-cover" />
                                </div>
                                <ChevronDown size={14} className={`text-gray-400 transition-transform duration-300 ${isProfileOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {/* Popover */}
                            {isProfileOpen && (
                                <>
                                    {/* Backdrop for closing */}
                                    <div 
                                        className="fixed inset-0 z-40" 
                                        onClick={() => setIsProfileOpen(false)}
                                    />
                                    <ProfilePopover 
                                        user={user} 
                                        onClose={() => setIsProfileOpen(false)} 
                                    />
                                </>
                            )}
                        </div>

                        <button
                            onClick={handleLogout}
                            className="hidden md:flex items-center gap-2 px-5 py-2.5 bg-[#5B0019] text-white text-sm font-semibold rounded-xl hover:bg-red-700 transition-all shadow-md active:scale-95"
                        >
                            <LogOut size={18} />
                            Đăng xuất
                        </button>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar">
                    {children}
                </div>
            </main>
        </div>
    );
}