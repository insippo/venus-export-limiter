import React from 'react';
import {
	Composition,
	registerRoot,
	useCurrentFrame,
	useVideoConfig,
	interpolate,
	spring,
	AbsoluteFill,
	Sequence,
} from 'remotion';

// =============================================================================
// 1. TÜÜBID, ANDMED JA DISAIN (Types, Data & Theme)
// =============================================================================

interface MonthlyData {
	month: string;
	revenue: number;
	costs: number;
	profit: number;
	visitors: number;
	summary: string;
}

const DATA: MonthlyData[] = [
	{ month: 'Jaanuar', revenue: 12000, costs: 8000, profit: 4000, visitors: 1500, summary: 'Aluslaius ja stabilisatsioon.' },
	{ month: 'Veebruar', revenue: 15000, costs: 8500, profit: 6500, visitors: 1800, summary: 'Kasvav huvi turul.' },
	{ month: 'Märts', revenue: 18000, costs: 9000, profit: 9000, visitors: 2200, summary: 'Esimene märkimisväärne hüpe.' },
	{ month: 'Aprill', revenue: 14000, costs: 10000, profit: 4000, visitors: 2100, summary: 'Korduv kulu kütise tõus.' },
	{ month: 'Mai', revenue: 22000, costs: 11000, profit: 11000, visitors: 2800, summary: 'Springimise periood.' },
	{ month: 'Juuni', revenue: 25000, costs: 12000, profit: 13000, visitors: 3200, summary: 'Suurem külastajate arv.' },
	{ month: 'Juuli', revenue: 23000, costs: 11500, profit: 11500, visitors: 3000, summary: 'Lõõgastunud kasv.' },
	{ month: 'August', revenue: 27000, costs: 13000, profit: 14000, visitors: 3500, summary: 'Reklaamikampaania mõju.' },
	{ month: 'September', revenue: 30000, costs: 14000, profit: 16000, visitors: 4000, summary: 'Stabiilne upward trend.' },
	{ month: 'Oktoober', revenue: 35000, costs: 16000, profit: 19000, visitors: 4500, summary: 'Rekordiline tuluepik.' },
	{ month: 'November', revenue: 32000, costs: 15000, profit: 17000, visitors: 4200, summary: 'Lühiajaline korrektsioon.' },
	{ month: 'Detsember', revenue: 45000, costs: 18000, profit: 27000, visitors: 5500, summary: 'Aasta suurim saavutus!' },
];

const THEME = {
	background: '#0d1117',
	text: '#c9d1d9',
	accent: '#58a6ff',
	secondary: '#30363d',
	chartArea: 'rgba(88, 166, 255, 0.15)',
};

// =============================================================================
// 2. ALAKOMPONENDID (Sub-components)
// =============================================================================

/**
 * Sissejuhatus: Animeeritud logo ja pealkiri
 */
export const Intro: React.FC = () => {
	const frame = useCurrentFrame();

	const entrance = spring({
		frame,
		fps: 30,
		config: {
			damping: 12,
			stiffness: 100,
		},
	});

	const opacity = interpolate(frame, [0, 20], [0, 1], {
		extrapolateRight: 'clamp',
	});

	const scale = interpolate(entrance, [0, 1], [0.5, 1]);

	return (
		<AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.background }}>
			<div style={{ transform: `scale(${scale})`, opacity, textAlign: 'center' }}>
				<div style={{
					width: 120,
					height: 120,
					backgroundColor: THEME.accent,
					borderRadius: '24px',
					margin: '0 auto 30px auto',
					display: 'flex',
					justifyContent: 'center',
					alignItems: 'center',
					fontSize: '60px',
					boxShadow: `0 0 40px ${THEME.accent}66`
				}}>
					📊
				</div>
				<h1 style={{ color: THEME.text, fontSize: '64px', margin: 0, fontFamily: 'sans-serif', letterSpacing: '-2px' }}>
					Dashboard <span style={{ color: THEME.accent }}>Report</span>
				</h1>
				<p style={{ color: THEME.text, opacity: 0.6, fontSize: '24px', fontFamily: 'sans-serif', margin: '10px 0 0 0' }}>
					Aasta finantsanalüüs
				</p>
			</div>
		</AbsoluteFill>
	);
};

/**
 * Graafik: SVG Area Chart
 */
interface ChartProps {
	data: MonthlyData[];
}

export const AreaChart: React.FC<ChartProps> = ({ data }) => {
	const frame = useCurrentFrame();
	const { width, height } = useVideoConfig();

	const chartWidth = width * 0.9;
	const chartHeight = height * 0.45;
	const padding = 60;

	const maxRevenue = Math.max(...data.map(d => d.revenue));

	// Punktide arvutus graafikule
	const points = data.map((d, i) => {
		const x = padding + (i * (chartWidth - padding * 2) / (data.length - 1));
		const y = (chartHeight - padding) - (d.revenue / maxRevenue * (chartHeight - padding * 2));
		return { x, y, revenue: d.revenue };
	});

	// SVG 'd' joonte ja ala jaoks
	const pathD = points.map((p, i) => {
		return i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`;
	}).join(' ');

	const areaD = `${pathD} L ${points[points.length - 1].x} ${chartHeight - padding} L ${points[0].x} ${chartHeight - padding} Z`;

	// Animatsiooni edenemine vahemikus 0 kuni 550 kaadrit (stseeni sees)
	const progress = interpolate(frame, [0, 550], [0, 1], {
		extrapolateRight: 'clamp',
		extrapolateLeft: 'clamp'
	});

	return (
		<svg width={chartWidth} height={chartHeight} style={{ overflow: 'visible' }}>
			{/* Horisontaalsed ruudustiku jooned */}
			{[0, 0.25, 0.5, 0.75, 1].map((tick, i) => (
				<line
					key={i}
					x1={padding}
					y1={padding + (chartHeight - padding * 2) * tick}
					x2={chartWidth - padding}
					y2={padding + (chartHeight - padding * 2) * tick}
					stroke={THEME.secondary}
					strokeWidth="1"
				/>
			))}

			{/* Täidetud ala joone all */}
			<path d={areaD} fill={THEME.chartArea} opacity={progress} />

			{/* Peamine graafiku joon */}
			<path
				d={pathD}
				fill="none"
				stroke={THEME.accent}
				strokeWidth="5"
				strokeLinecap="round"
				strokeLinejoin="round"
				strokeDasharray={2000}
				strokeDashoffset={2000 * (1 - progress)}
			/>

			{/* Andmepunktid ja väärtused */}
			{points.map((p, i) => {
				const pointProgress = i / data.length;
				const pointOpacity = interpolate(
					progress,
					[pointProgress, pointProgress + 0.05],
					[0, 1],
					{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
				);
				return (
					<g key={i} opacity={pointOpacity}>
						<circle cx={p.x} cy={p.y} r="8" fill={THEME.accent} stroke={THEME.background} strokeWidth="3" />
						{i % 2 === 0 && (
							<text
								x={p.x}
								y={p.y - 20}
								fontSize="16"
								textAnchor="middle"
								fill={THEME.text}
								fontWeight="bold"
								fontFamily="sans-serif"
							>
								${Math.round(p.revenue / 1000)}k
							</text>
						)}
					</g>
				);
			})}
		</svg>
	);
};

/**
 * Andmestseen: Graafik ja alumine andmete paneel
 */
export const DataScene: React.FC = () => {
	const frame = useCurrentFrame();

	// 600 kaadrit jagatud 12 kuuga = 50 kaadrit iga kuu kuva
	const currentMonthIndex = Math.min(Math.floor(frame / 50), DATA.length - 1);
	const currentData = DATA[currentMonthIndex >= 0 ? currentMonthIndex : 0];

	const titleOpacity = interpolate(frame % 50, [0, 15], [0.4, 1], {
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{ backgroundColor: THEME.background, padding: '60px', fontFamily: 'sans-serif' }}>
			<div style={{ marginBottom: '40px', opacity: titleOpacity }}>
				<h2 style={{ color: THEME.accent, margin: '0 0 10px 0', fontSize: '40px' }}>
					{currentData.month} Raport
				</h2>
				<p style={{ color: THEME.text, fontSize: '24px', opacity: 0.8, margin: 0 }}>
					{currentData.summary}
				</p>
			</div>

			<div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
				<AreaChart data={DATA} />
			</div>

			{/* Alumine andmetabel */}
			<div style={{
				display: 'flex',
				justifyContent: 'space-between',
				marginTop: '40px',
				padding: '30px',
				backgroundColor: THEME.secondary,
				borderRadius: '16px'
			}}>
				<div>
					<div style={{ color: '#8b949e', fontSize: '18px', marginBottom: '5px' }}>Käive</div>
					<div style={{ color: THEME.accent, fontSize: '32px', fontWeight: 'bold' }}>
						${currentData.revenue.toLocaleString()}
					</div>
				</div>
				<div>
					<div style={{ color: '#8b949e', fontSize: '18px', marginBottom: '5px' }}>Külastajad</div>
					<div style={{ color: THEME.text, fontSize: '32px', fontWeight: 'bold' }}>
						{currentData.visitors.toLocaleString()}
					</div>
				</div>
				<div>
					<div style={{ color: '#8b949e', fontSize: '18px', marginBottom: '5px' }}>Kasum</div>
					<div style={{ color: '#3fb950', fontSize: '32px', fontWeight: 'bold' }}>
						+${currentData.profit.toLocaleString()}
					</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

/**
 * Lõpetus (Outro): Pulseeriv siinusfunktsiooniga Call to Action stseen
 */
export const Outro: React.FC = () => {
	const frame = useCurrentFrame();
	const scale = 1 + Math.sin(frame * 0.15) * 0.05;
	const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

	return (
		<AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: THEME.background, fontFamily: 'sans-serif' }}>
			<div style={{ textAlign: 'center', opacity: fadeIn }}>
				<h2 style={{ color: THEME.text, fontSize: '48px', margin: '0 0 20px 0' }}>
					Tahad näha rohkem?
				</h2>
				<p style={{ color: THEME.text, opacity: 0.6, fontSize: '22px', marginBottom: '40px' }}>
					Külasta meie platvormi ja analüüsi andmeid reaalajas.
				</p>
				<div style={{
					transform: `scale(${scale})`,
					backgroundColor: THEME.accent,
					color: THEME.background,
					padding: '18px 40px',
					borderRadius: '30px',
					fontSize: '24px',
					fontWeight: 'bold',
					display: 'inline-block',
					boxShadow: `0 0 30px ${THEME.accent}44`
				}}>
					Vaata Dashboardi 🚀
				</div>
			</div>
		</AbsoluteFill>
	);
};

// =============================================================================
// 3. PEAKOMPONENT JA REGISTREERIMINE (Composition Setup & Entry Point)
// =============================================================================

export const MainComposition: React.FC = () => {
	return (
		<AbsoluteFill>
			{/* Intro: 0 - 5 sekundit (150 kaadrit) */}
			<Sequence from={0} durationInFrames={150}>
				<Intro />
			</Sequence>

			{/* Andmete stseen: 5 - 25 sekundit (600 kaadrit) */}
			<Sequence from={150} durationInFrames={600}>
				<DataScene />
			</Sequence>

			{/* Outro: 25 - 30 sekundit (150 kaadrit) */}
			<Sequence from={750} durationInFrames={150}>
				<Outro />
			</Sequence>
		</AbsoluteFill>
	);
};

const FPS = 30;
const DURATION_SECONDS = 30;
const DURATION_IN_FRAMES = FPS * DURATION_SECONDS;

const RemotionRoot: React.FC = () => {
	return (
		<Composition
			id="DashboardReport"
			component={MainComposition}
			durationInFrames={DURATION_IN_FRAMES}
			fps={FPS}
			width={1920}
			height={1080}
		/>
	);
};

registerRoot(RemotionRoot);
