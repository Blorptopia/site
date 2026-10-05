import { Task, TaskStatus } from "@lit/task";
import { css, html, LitElement, type CSSResultGroup, type HTMLTemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { map } from "lit/directives/map.js";
import { range } from "lit/directives/range.js";
import { ref, createRef, type Ref } from "lit/directives/ref.js";
import FlaskImageURL from "../images/flask/image.png";
import MaskImageURL from "../images/flask/mask.png";
import Color, { type ColorInstance } from "color";

const FLASK_BASELINE_TEMPERATURE = 20;
const FLASK_MAX_TEMPERATURE = 100;
const FLASK_HEAT_SPEED = 0.05;
const FLASK_MAX_OVERHEAT_SCORE = 40;
const FLASK_REQUIRED_ROTATION: number = 10 * 2 * Math.PI;
const FLASK_LIQUID_RESOLUTION: number = 20;
const FLASK_MAX_LIQUID: number = 10;
const FLASK_WAVE_LENGTH: number = 10;
const FLASK_DEFAULT_WAVE_CYCLE_INTERVAL: number = 1000;

@customElement("bb-curse-flask-visualization")
export class CurseFlaskVisualizationElement extends LitElement {
	// Props
	@property({type: Array})
	public controls: string[];
	@property({type: Array})
	public parts?: string[];
	@property({type: Array})
	public temperature: number;
	@property({type: Boolean})
	public heated: boolean;
	@property({type: String})
	public temperatureMode: "manual" | "heat";
	@property({type: Number})
	public waveCycleInterval: number;

	// State
	private overrideReduceMotion: boolean;

	// Elements
	private canvasRef: Ref<HTMLCanvasElement>;
	private temperatureInputRef: Ref<HTMLInputElement>;

	// Attributes
	private renderTask: Task<[HTMLCanvasElement | undefined, boolean], void>;


	public constructor() {
		super();
		this.controls = [];

		this.temperature = FLASK_BASELINE_TEMPERATURE;
		this.heated = false;
		this.temperatureMode = "manual";
		this.waveCycleInterval = FLASK_DEFAULT_WAVE_CYCLE_INTERVAL;

		this.overrideReduceMotion = false;

		this.canvasRef = createRef();
		this.temperatureInputRef = createRef();

		const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

		const flaskImage = new Image();
		flaskImage.src = FlaskImageURL;
		const maskImage = new Image();
		maskImage.src = MaskImageURL;
		
		this.renderTask = new Task(this, {
			task: async ([canvas, overrideReduceMotion], { signal }) => {
				if (canvas === undefined) {
					console.log("no canvas defined; ending rendering task");
					return;
				}
				const context = canvas.getContext("2d")!;
				while (!signal.aborted) {
					context.reset();
					context.save();
					if (this.parts === undefined || this.parts.includes("mask")) {
						context.imageSmoothingEnabled = false;
						context.drawImage(maskImage, 0, 0, canvas.width, canvas.height);
						context.globalCompositeOperation = "source-in";
					}
					
					
					if (this.parts === undefined || this.parts.includes("liquid")) {
						const ingredientsCanvas = this.drawIngredients(canvas.width, canvas.height)!;
						context.drawImage(ingredientsCanvas, 0, 0);
					}
					context.restore();

					if (this.parts === undefined || this.parts.includes("flask")) {
						context.drawImage(flaskImage, 0, 0, canvas.width, canvas.height);
					}

					if (reduceMotion && !overrideReduceMotion) {
						console.log("stopping animation due to reduced motion");
						break;
					}

					await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
				}
			},
			args: () => [this.canvasRef.value, this.overrideReduceMotion] as const,
			onError: (error) => console.error(error)
		});
		this.updateTemperatureTask = new Task(this, {
			task: async ([], {signal}) => {
				while (!signal.aborted) {
					if (this.heated) {
						await new Promise<void>(resolve => setTimeout(resolve, 300));
						this.temperature += 3;
					} else {
						await new Promise<void>(resolve => setTimeout(resolve, 500));
						this.temperature -= 1;
					}
					this.temperature = Math.max(FLASK_BASELINE_TEMPERATURE, this.temperature);

					const instances = this.querySelectorAll("bb-curse-flask-ingredient-instance");

					instances.forEach(instance => {
						let heatedFraction = parseFloat(instance.getAttribute("heatedfraction") ?? "0");
						const heatEffect = (this.temperature - FLASK_BASELINE_TEMPERATURE) / FLASK_MAX_TEMPERATURE;
						heatedFraction += heatEffect * FLASK_HEAT_SPEED;
						
						let wronglyHeatedScore = parseInt(instance.getAttribute("heatedwrongscore") ?? "0");
						const rawMinTemp = instance.getAttribute("temperaturemin");
						let minTemp: number | undefined = undefined;
						if (rawMinTemp !== undefined) {
							minTemp = parseFloat(rawMinTemp);
						}
						const rawMaxTemp = instance.getAttribute("temperaturemax");
						let maxTemp: number | undefined = undefined;
						if (rawMaxTemp !== undefined) {
							maxTemp = parseFloat(rawMaxTemp);
						}
						if (minTemp !== undefined && this.temperature < minTemp) {
							wronglyHeatedScore++;
						}
						if (maxTemp !== undefined && this.temperature > maxTemp) {
							wronglyHeatedScore++;
						}

						instance.setAttribute("heatedfraction", heatedFraction);
						instance.setAttribute("heatedwrongscore", wronglyHeatedScore);

						return {
							...instance,
							heatedFraction,
							wronglyHeatedScore
						}
					});
				}
			},
			args: () => [] as const,
			onError: (error) => console.error(error)
		});
	}



	protected render(): HTMLTemplateResult {
		return html`
			<div id="flask-container">
				<div id="flask">
					<canvas ${ref(this.canvasRef)}></canvas>
				</div>
			</div>
			<div id="controls">
				<div class="control" ?hidden=${this.renderTask.status === TaskStatus.PENDING}>
					<button @click=${() => this.overrideReduceMotion = true}>Enable animation</button>
				</div>
				<div class="control" ?hidden=${!this.controls.includes("heat")}>
					<label for="input-heated">Heated</label>
					<input
						id="input-heated"
						type="checkbox"
						?checked=${this.heated}
						@input=${() => {
							this.heated = !this.heated;
						}}
					>
				</div>
				<div class="control" ?hidden=${!this.controls.includes("temperature")}>
					<label for="input-heated">Temperature</label>
					<input
						${ref(this.temperatureInputRef)}
						id="input-temperature"
						type="range"
						min=${FLASK_BASELINE_TEMPERATURE}
						max=${FLASK_MAX_TEMPERATURE}
						.value=${this.temperature}
						@input=${() => {
							this.temperature = this.temperatureInputRef.value!.value;
						}}
					>
				</div>
				<div class="control" ?hidden=${!this.controls.includes("reset")}>
					<button
						@click=${() => {
							const instances = this.querySelectorAll("bb-curse-flask-ingredient-instance");
							instances.forEach(instance => {
								instance.removeAttribute("heatedfraction");
								instance.removeAttribute("heatedwrongscore");
								instance.removeAttribute("totalrotation");
							});
							this.temperature = this.temperatureInputRef.value!.value;
						}}
					>
				</div>
			</div>
		`;
	}
	private drawIngredients(canvasWidth: number, canvasHeight: number): HTMLCanvasElement | undefined {
		const instances = Array.from(this.querySelectorAll("bb-curse-flask-ingredient-instance"));

		const canvas = document.createElement("canvas");
		const context = canvas.getContext("2d")!;
		canvas.width = canvasWidth;
		canvas.height = canvasHeight;

		const angleIncrement = (Math.PI * 2) / FLASK_LIQUID_RESOLUTION;
		let wave: number[] = [];

		
		for (let index = 0; index <= FLASK_LIQUID_RESOLUTION; index++) {
			let point = Math.sin(angleIncrement * index) * FLASK_WAVE_LENGTH;
			if (this.waveCycleInterval >= 0) {
				point = Math.sin(angleIncrement * index + Date.now() / this.waveCycleInterval) * FLASK_WAVE_LENGTH;
			}
			
			// Add variation due to temperature
			point += Math.min(6, Math.random() * (this.temperature - FLASK_BASELINE_TEMPERATURE) / 10);

			wave.push(point);
		}

		let ingredientIndex = 0;

		for (const instance of instances.toReversed()) {
			const liquidScale = canvasHeight / FLASK_MAX_LIQUID;

			const height = canvasHeight + liquidScale * (ingredientIndex + 1) - liquidScale * instances.length;

			const colorAfterEffects = this.getInstanceColor(instance);
			
			const shouldRenderBackWave = this.parts === undefined || this.parts.includes("backwave");
			if (ingredientIndex === 0 && shouldRenderBackWave) {
				context.fillStyle = colorAfterEffects.darken(.2).toString();
				context.beginPath();
				context.moveTo(0, height);
				for (let [index, point] of wave.entries()) {
					context.lineTo(canvas.width / FLASK_LIQUID_RESOLUTION * index, height + point - FLASK_WAVE_LENGTH * 2);
				}
				context.lineTo(canvas.width, canvas.height);
				context.lineTo(0, canvas.height);
				context.fill();
			}

			context.fillStyle = colorAfterEffects.toString();
			context.beginPath();
			context.moveTo(0, height);
			for (let [index, point] of wave.toReversed().entries()) {
				context.lineTo(canvas.width / FLASK_LIQUID_RESOLUTION * index, height + point - FLASK_WAVE_LENGTH * 2);
			}
			context.lineTo(canvas.width, canvas.height);
			context.lineTo(0, canvas.height);
			context.fill();

			ingredientIndex++;
		}
		
		return canvas;
	}
	private getInstanceColor(instance: HTMLElement): ColorInstance {
		let color = new Color(instance.getAttribute("basecolor"));

		// Make more transparent depending on how little it's cooked
		const heatedFraction = parseFloat(instance.getAttribute("heatedfraction") ?? "0");
		const transparent = new Color("transparent");
		color = color.mix(transparent, 1 - Math.max(0.2, Math.min(1, heatedFraction)));
		
		if (heatedFraction > 1) {
			const brown = new Color("brown");
			color = color.mix(brown, Math.min(1, heatedFraction - 1));
		}


		const black = new Color("black");
		const wronglyHeatedScore = parseFloat(instance.getAttribute("heatedwrongscore") ?? "0");
		const wronglyHeatedFraction = Math.min(wronglyHeatedScore, FLASK_MAX_OVERHEAT_SCORE) / FLASK_MAX_OVERHEAT_SCORE;
		color = color.mix(black, wronglyHeatedFraction / 2);

		// const purple = new Color("#ae3ed1");
		// color = color.mix(purple, instance.poisonFraction / 2);
		
		const rotationDegrees = parseFloat(instance.getAttribute("totalrotation") ?? "0");
		const mixedFraction = Math.min(rotationDegrees / FLASK_REQUIRED_ROTATION, 1);
		color = color.desaturate(1 - mixedFraction);

		return color;
		
	}
	static styles?: CSSResultGroup = css`
		#flask-container {
			display: inline-block;
			background: #b679c3;
			padding: 1rem;
		}
		#flask {
			display: block;
			--source-height: 109;
			--source-width: 74;
			--size-multiplier: 0.05rem;
			height: calc(var(--source-height) * var(--size-multiplier));
			width: calc(var(--source-width) * var(--size-multiplier));
			position: relative;
		}
		canvas {
			position: absolute;
			top: 0;
			left: 0;
			height: 100%;
			width: 100%;

			pointer-events: none;
		}
	`;
}

