from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
import sys
import os

# إضافة المسار الأساسي لكي يتمكن من استيراد shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.config import settings
from shared.database import AsyncSessionLocal
from shared.models import Guild, User
from sqlalchemy import select, func

app = FastAPI(title="TS BOT Dashboard")

@app.get("/api/stats")
async def get_stats():
    async with AsyncSessionLocal() as session:
        guilds_count = (await session.execute(select(func.count()).select_from(Guild))).scalar() or 0
        users_count = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
        
    return {
        "guilds": guilds_count,
        "users": users_count
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    html_content = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة تحكم TS BOT</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #2c2f33; color: #fff; text-align: center; padding: 50px; margin: 0; }
            .container { max-width: 800px; margin: 0 auto; background: rgba(30, 30, 40, 0.8); padding: 40px; border-left: 6px solid #ff0000; border-radius: 5px; box-shadow: 0 8px 32px rgba(0,0,0,0.5); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
            h1 { color: #ff4500; font-size: 2.5em; margin-bottom: 10px; }
            p { font-size: 1.2em; line-height: 1.8; color: #dddddd; }
            .btn { display: inline-block; padding: 12px 24px; background: #ff4500; color: #fff; text-decoration: none; border-radius: 8px; margin-top: 30px; font-weight: bold; transition: background 0.3s; }
            .btn:hover { background: #e03e00; }
            .status { margin-top: 40px; padding: 20px; background: rgba(255, 69, 0, 0.1); border-left: 5px solid #ff4500; border-radius: 5px; text-align: right; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin-top: 30px; }
            .stat-card { background: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); }
            .stat-card h2 { color: #5865F2; font-size: 2em; margin: 0; }
            .stat-card p { font-size: 1em; margin: 5px 0 0; color: #fff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ TS BOT (The Sanctuary)</h1>
            <p>مرحباً بك في لوحة تحكم أذكى بوت ديسكورد مبني بالكامل على الذكاء الاصطناعي (OpenRouter).</p>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h2 id="guildsCount">...</h2>
                    <p>سيرفر نشط</p>
                </div>
                <div class="stat-card">
                    <h2 id="usersCount">...</h2>
                    <p>مستخدم</p>
                </div>
            </div>

            <div class="status">
                <h3>🚀 الأنظمة الذكية النشطة حالياً:</h3>
                <ul>
                    <li><strong>Guard AI:</strong> حماية ذكية وتحليل عميق للرسائل.</li>
                    <li><strong>Level AI:</strong> مستويات مبنية على جودة وكمية الأحرف المكتوبة.</li>
                    <li><strong>Economy & Support AI:</strong> اقتصاد تفاعلي ودعم فني آلي.</li>
                    <li><strong>Event AI:</strong> مراقبة الخمول وإطلاق فعاليات تلقائية.</li>
                </ul>
            </div>
            
            <a href="#" class="btn">تسجيل الدخول باستخدام ديسكورد</a>
        </div>
        
        <script>
            async function fetchStats() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    document.getElementById('guildsCount').innerText = data.guilds;
                    document.getElementById('usersCount').innerText = data.users;
                } catch (error) {
                    console.error('Error fetching stats:', error);
                }
            }
            fetchStats();
            setInterval(fetchStats, 30000); // تحديث كل 30 ثانية
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.dashboard_host, port=settings.dashboard_port)
