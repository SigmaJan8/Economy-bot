import discord
from discord.ext import commands
from storage import get_user_data, update_user_data, load_data, save_data
from config import BUSINESS_FILE, APPLICATIONS_FILE
from datetime import datetime
from math import floor
import asyncio
import random

class Business(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ========== CREATE BUSINESS ==========
    @commands.hybrid_command(name='create_business', description='Create your own business')
    async def create_business(self, ctx, name: str, *, description: str):
        user_data = get_user_data(ctx.author.id)
        businesses = load_data(BUSINESS_FILE)
        for business in businesses.values():
            if business['owner_id'] == ctx.author.id:
                await ctx.send("❌ You already own a business!", ephemeral=True)
                return
        creation_fee = 5000
        if user_data['balance'] + user_data['bank'] < creation_fee:
            await ctx.send(f"❌ You need ${creation_fee:,} to create a business!\nYour net worth: ${user_data['balance'] + user_data['bank']:,}", ephemeral=True)
            return
        if user_data['bank'] >= creation_fee:
            user_data['bank'] -= creation_fee
        else:
            remaining = creation_fee - user_data['bank']
            user_data['bank'] = 0
            user_data['balance'] -= remaining
        business_id = f"biz_{ctx.author.id}_{int(datetime.now().timestamp())}"
        businesses[business_id] = {
            'id': business_id,
            'name': name,
            'description': description,
            'owner_id': ctx.author.id,
            'owner_name': ctx.author.display_name,
            'level': 1,
            'employees': {},
            'max_employees': 3,
            'work_bonus': 1.5,
            'created_at': datetime.now().isoformat(),
            'upgrades': {
                'premium_office': False,
                'employee_benefits': False,
                'marketing_boost': False,
                'security_system': False
            },
            'revenue': 0,
            'total_employees_hired': 0
        }
        update_user_data(ctx.author.id, user_data)
        save_data(BUSINESS_FILE, businesses)
        embed = discord.Embed(
            title="🏢 Business Created!",
            description=f"**{name}** has been established!\n\n📝 {description}",
            color=0x00ff00
        )
        embed.add_field(name="💰 Creation Fee", value=f"${creation_fee:,}", inline=True)
        embed.add_field(name="👥 Max Employees", value="3", inline=True)
        embed.add_field(name="📈 Work Bonus", value="1.5x", inline=True)
        await ctx.send(embed=embed)

    # ========== BUSINESS LIST / APPLY ==========
    @commands.hybrid_command(name='business', description='View business information or apply to work')
    async def business(self, ctx, action: str = "list", *, business_name: str = None):
        businesses = load_data(BUSINESS_FILE)
        if action.lower() == "list":
            if not businesses:
                await ctx.send("🏢 No businesses found. Use `/create_business` to start one.", ephemeral=True)
                return
            embed = discord.Embed(title="🏢 Available Businesses", color=0x0099ff)
            for business in businesses.values():
                employee_count = len(business['employees'])
                max_employees = business['max_employees']
                hiring_status = "🟢 Hiring" if employee_count < max_employees else "🔴 Full"
                embed.add_field(
                    name=f"{business['name']} (Level {business['level']})",
                    value=f"👤 Owner: {business['owner_name']}\n"
                          f"📝 {business['description'][:100]}{'...' if len(business['description']) > 100 else ''}\n"
                          f"👥 Employees: {employee_count}/{max_employees} {hiring_status}\n"
                          f"💰 Work Bonus: {business['work_bonus']}x",
                    inline=False
                )
            embed.set_footer(text="Use `/business apply <business_name>` to apply for a job!")
            await ctx.send(embed=embed)
        elif action.lower() == "apply":
            if not business_name:
                await ctx.send("❌ Please specify which business you want to apply to!", ephemeral=True)
                return
            # Find business by name
            target_business = None
            for business in businesses.values():
                if business['name'].lower() == business_name.lower():
                    target_business = business
                    break
            if not target_business:
                await ctx.send(f"❌ No business named '{business_name}' was found.", ephemeral=True)
                return
            if len(target_business['employees']) >= target_business['max_employees']:
                await ctx.send(f"❌ **{target_business['name']}** is not currently hiring.", ephemeral=True)
                return
            if str(ctx.author.id) in target_business['employees']:
                await ctx.send(f"❌ You already work at **{target_business['name']}**!", ephemeral=True)
                return
            # Prompt user for application input
            await ctx.send("Why do you want to work here? (Type your answer below, 500 chars max)")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                reason_msg = await self.bot.wait_for('message', timeout=60, check=check)
            except asyncio.TimeoutError:
                await ctx.send("Timed out! Please try again.")
                return
            await ctx.send("Describe your previous experience (or type 'none'):")
            try:
                experience_msg = await self.bot.wait_for('message', timeout=60, check=check)
            except asyncio.TimeoutError:
                await ctx.send("Timed out! Please try again.")
                return
            await ctx.send("What is your availability? (e.g. evenings, weekends, etc.)")
            try:
                avail_msg = await self.bot.wait_for('message', timeout=60, check=check)
            except asyncio.TimeoutError:
                await ctx.send("Timed out! Please try again.")
                return
            # Save application
            applications = load_data(APPLICATIONS_FILE)
            app_id = f"app_{ctx.author.id}_{target_business['id']}_{int(datetime.now().timestamp())}"
            applications[app_id] = {
                'id': app_id,
                'business_id': target_business['id'],
                'business_name': target_business['name'],
                'applicant_id': ctx.author.id,
                'applicant_name': ctx.author.display_name,
                'reason': reason_msg.content[:500],
                'experience': experience_msg.content[:300],
                'availability': avail_msg.content[:100],
                'status': 'pending',
                'applied_at': datetime.now().isoformat()
            }
            save_data(APPLICATIONS_FILE, applications)
            # DM business owner
            try:
                owner = await self.bot.fetch_user(target_business['owner_id'])
                if owner:
                    embed = discord.Embed(
                        title="📋 New Job Application!",
                        description=f"**{ctx.author.display_name}** applied to work at **{target_business['name']}**",
                        color=0x0099ff
                    )
                    embed.add_field(name="Why they want to work here:", value=reason_msg.content, inline=False)
                    embed.add_field(name="Experience:", value=experience_msg.content, inline=True)
                    embed.add_field(name="Availability:", value=avail_msg.content, inline=True)
                    embed.set_footer(text="Use /manage_business to approve or deny applications")
                    await owner.send(embed=embed)
            except Exception:
                pass
            await ctx.send(f"✅ Your application to **{target_business['name']}** has been sent!", ephemeral=True)

    # ========== MANAGE BUSINESS ==========
    @commands.hybrid_command(name='manage_business', description='Manage your business (owner only)')
    async def manage_business(self, ctx):
        businesses = load_data(BUSINESS_FILE)
        user_business = None
        for business in businesses.values():
            if business['owner_id'] == ctx.author.id:
                user_business = business
                break
        if not user_business:
            await ctx.send("❌ You don't own a business! Use `/create_business` to start one.", ephemeral=True)
            return
        # Show management panel
        employee_list = []
        for emp_id, emp_data in user_business['employees'].items():
            employee_list.append(f"👤 {emp_data['name']} (Sessions: {emp_data['total_work_sessions']})")
        embed = discord.Embed(
            title=f"🏢 Managing: {user_business['name']}",
            description=user_business['description'],
            color=0x0099ff
        )
        embed.add_field(
            name=f"👥 Employees ({len(user_business['employees'])}/{user_business['max_employees']})",
            value="\n".join(employee_list) if employee_list else "No employees",
            inline=False
        )
        embed.add_field(name="📈 Level", value=user_business['level'], inline=True)
        embed.add_field(name="💰 Work Bonus", value=f"{user_business['work_bonus']}x", inline=True)
        embed.add_field(name="👔 Total Hired", value=user_business['total_employees_hired'], inline=True)
        await ctx.send(embed=embed)
        # Application approval/denial/firing via chat not implemented for brevity

    # ========== UPGRADE BUSINESS ==========
    @commands.hybrid_command(name='upgrade_business', description='Upgrade your business with various improvements')
    async def upgrade_business(self, ctx):
        businesses = load_data(BUSINESS_FILE)
        user_business = None
        for business in businesses.values():
            if business['owner_id'] == ctx.author.id:
                user_business = business
                break
        if not user_business:
            await ctx.send("❌ You don't own a business! Use `/create_business` to start one.", ephemeral=True)
            return
        upgrades = {
            'premium_office': {'name': 'Premium Office', 'cost': 10000, 'desc': 'Double employee capacity (3→6)'},
            'employee_benefits': {'name': 'Employee Benefits', 'cost': 7500, 'desc': 'Increase work bonus by 0.5x'},
            'marketing_boost': {'name': 'Marketing Boost', 'cost': 5000, 'desc': 'Attract more job applicants'},
            'security_system': {'name': 'Security System', 'cost': 8000, 'desc': 'Protect from theft events'}
        }
        embed = discord.Embed(
            title=f"🔧 Upgrades for {user_business['name']}",
            description="Invest in your business to make it more profitable!",
            color=0x9932cc
        )
        for key, info in upgrades.items():
            status = "✅ Owned" if user_business['upgrades'][key] else f"💰 ${info['cost']:,}"
            embed.add_field(name=f"{info['name']} - {status}", value=info['desc'], inline=False)
        await ctx.send(embed=embed)
        await ctx.send("Type the name of the upgrade you wish to purchase (or 'cancel'):")
        def check(m): return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await self.bot.wait_for('message', timeout=30, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out! Please try again.")
            return
        chosen = None
        for key, info in upgrades.items():
            if msg.content.lower() == info['name'].lower():
                chosen = key
        if not chosen:
            await ctx.send("Cancelled or not a valid upgrade.")
            return
        if user_business['upgrades'][chosen]:
            await ctx.send("This upgrade has already been purchased!")
            return
        user_data = get_user_data(ctx.author.id)
        cost = upgrades[chosen]['cost']
        if user_data['balance'] + user_data['bank'] < cost:
            await ctx.send(f"You need ${cost:,} for this upgrade!\nYour net worth: ${user_data['balance'] + user_data['bank']:,}")
            return
        if user_data['bank'] >= cost:
            user_data['bank'] -= cost
        else:
            remaining = cost - user_data['bank']
            user_data['bank'] = 0
            user_data['balance'] -= remaining
        user_business['upgrades'][chosen] = True
        if chosen == 'premium_office':
            user_business['max_employees'] = 6
        elif chosen == 'employee_benefits':
            user_business['work_bonus'] += 0.5
        businesses[user_business['id']] = user_business
        update_user_data(ctx.author.id, user_data)
        save_data(BUSINESS_FILE, businesses)
        await ctx.send(f"✅ Upgrade purchased! {upgrades[chosen]['desc']}")

    # ========== WORK COMMAND ==========
    @commands.hybrid_command(name='work', description='Work to earn money')
    async def work(self, ctx):
        user_data = get_user_data(ctx.author.id)
        if user_data['last_work']:
            from datetime import datetime, timedelta
            last_time = datetime.fromisoformat(user_data['last_work'])
            if datetime.now() < last_time + timedelta(hours=1):
                next_time = last_time + timedelta(hours=1)
                await ctx.send(f"You can work again <t:{int(next_time.timestamp())}:R>")
                return
        work_scenarios = [
            ("You delivered pizzas around town", random.randint(50, 150)),
            ("You walked dogs in the neighborhood", random.randint(40, 120)),
            ("You helped at a local cafe", random.randint(60, 140)),
            ("You did freelance graphic design", random.randint(80, 200)),
            ("You tutored students online", random.randint(70, 180)),
            ("You worked as a cashier", random.randint(45, 130)),
            ("You did yard work for neighbors", random.randint(55, 160)),
            ("You worked at a bookstore", random.randint(50, 140)),
        ]
        scenario, earnings = random.choice(work_scenarios)
        total_bonus = 1.0
        bonus_sources = []
        job_bonuses = {
            "Manager": 1.5,
            "Developer": 1.8,
            "Teacher": 1.3,
            "Chef": 1.4,
            "Artist": 1.2
        }
        if user_data['job'] and user_data['job'] in job_bonuses:
            job_bonus = job_bonuses[user_data['job']]
            total_bonus *= job_bonus
            bonus_sources.append(f"Job ({user_data['job']}): {job_bonus}x")
        if user_data['business_job']:
            businesses = load_data(BUSINESS_FILE)
            business = businesses.get(user_data['business_job']['business_id'])
            if business:
                business_bonus = business['work_bonus']
                total_bonus *= business_bonus
                bonus_sources.append(f"Business ({business['name']}): {business_bonus}x")
                if str(ctx.author.id) in business['employees']:
                    business['employees'][str(ctx.author.id)]['total_work_sessions'] += 1
                    save_data(BUSINESS_FILE, businesses)
        final_earnings = floor(earnings * total_bonus)
        user_data['balance'] += final_earnings
        user_data['last_work'] = datetime.now().isoformat()
        update_user_data(ctx.author.id, user_data)
        embed = discord.Embed(
            title="💼 You Worked!",
            description=f"{scenario} and earned **${final_earnings:,}**!",
            color=0x00ff00
        )
        embed.add_field(name="🛠 Base Earnings", value=f"${earnings:,}", inline=True)
        embed.add_field(name="📈 Bonus Multiplier", value=f"{total_bonus:.2f}x", inline=True)
        embed.add_field(name="💰 Final Total", value=f"${final_earnings:,}", inline=True)
        if bonus_sources:
            embed.add_field(name="📋 Bonus Breakdown", value="\n".join(bonus_sources), inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Business(bot))
