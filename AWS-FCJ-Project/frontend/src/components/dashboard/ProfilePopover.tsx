"use client";
import React from 'react';
import Image from 'next/image';
import { User, Mail, Shield, Layers, School, X } from 'lucide-react';
import study from '../../../public/study.png';

interface ProfilePopoverProps {
    user: {
        name: string;
        email: string;
        role: string;
        class_name?: string;
        grade?: number;
    };
    onClose: () => void;
}

export const ProfilePopover: React.FC<ProfilePopoverProps> = ({ user, onClose }) => {
    const isStudent = user.role === 'student';

    return (
        <div className="absolute left-1/2 -translate-x-1/2 top-14 w-80 bg-white rounded-2xl shadow-2xl border border-gray-100 z-50 animate-in fade-in slide-in-from-top-2 duration-200 overflow-hidden">
            {/* Header / Background */}
            <div className="h-20 bg-[#5B0019] relative">
                <button 
                    onClick={onClose}
                    className="absolute top-2 right-2 p-1 text-white/50 hover:text-white transition-colors"
                >
                    <X size={18} />
                </button>
            </div>

            {/* Profile Info */}
            <div className="px-6 pb-8 pt-10 relative">
                {/* Large Avatar */}
                <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-24 h-24 rounded-full border-4 border-white shadow-lg overflow-hidden bg-white">
                    <Image src={study} alt="Profile Avatar" fill className="object-cover" />
                </div>

                <div className="text-center mb-6">
                    <h3 className="text-xl font-bold text-gray-800">{user.name || 'Người dùng'}</h3>
                    <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider">{user.role}</p>
                </div>

                <div className="space-y-4">
                    <InfoRow icon={<Mail size={16} className="text-[#5B0019]" />} label="Email" value={user.email} />
                    <InfoRow icon={<Shield size={16} className="text-[#5B0019]" />} label="Vai trò" value={user.role} />
                    
                    {isStudent && (
                        <>
                            <InfoRow icon={<Layers size={16} className="text-[#5B0019]" />} label="Khối" value={`${user.grade}`} />
                            <InfoRow icon={<School size={16} className="text-[#5B0019]" />} label="Lớp" value={user.class_name || 'N/A'} />
                        </>
                    )}
                </div>
            </div>
            
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-100 italic text-[11px] text-gray-400 text-center">
                EduTrust - Hệ thống giáo dục thông minh
            </div>
        </div>
    );
};

const InfoRow = ({ icon, label, value }: { icon: React.ReactNode, label: string, value: string }) => (
    <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
        <div className="w-8 h-8 rounded-full bg-[#5B0019]/5 flex items-center justify-center shrink-0">
            {icon}
        </div>
        <div className="flex flex-col">
            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">{label}</span>
            <span className="text-sm font-semibold text-gray-700 truncate max-w-[180px]">{value}</span>
        </div>
    </div>
);
